from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from domains.subscription.application.services.core.update.task_progress_service import (
    SubscriptionSyncTaskProgressService,
)
from domains.subscription.application.services.crawl.dispatcher.service import CrawlDispatcherService
from infrastructure.config.settings import settings
from workers.scheduling.executors.leases import CrawlWorkerLeaseTracker
from workers.scheduling.executors.tasks import CrawlWorkerTaskRunner

logger = logging.getLogger(__name__)


class CrawlWorkerRuntime:
    def __init__(
        self,
        *,
        dispatcher: CrawlDispatcherService | None = None,
        worker_id: str = 'crawl-worker-1',
        lease_seconds: int | None = None,
        retry_delay_seconds: int = 30,
        poll_interval_seconds: float = 1.0,
        max_concurrency: int | None = None,
        subscription_task_progress: SubscriptionSyncTaskProgressService | None = None,
    ):
        self.dispatcher = dispatcher or CrawlDispatcherService()
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds or settings.crawl.worker_lease_seconds
        self.retry_delay_seconds = retry_delay_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_concurrency = max(1, max_concurrency or settings.crawl.slots_per_process)
        self.task_runner = CrawlWorkerTaskRunner(
            worker_id=self.worker_id,
            retry_delay_seconds=self.retry_delay_seconds,
            subscription_task_progress=subscription_task_progress,
        )
        self._lease_tracker = CrawlWorkerLeaseTracker(worker_id=self.worker_id, lease_seconds=self.lease_seconds)

    def run_once(self) -> bool:
        now = datetime.now()
        self._recover_expired_tasks(now=now)
        task = self.dispatcher.claim_next(worker_id=self.worker_id, now=now, lease_seconds=self.lease_seconds)
        if not task:
            return False

        self.task_runner.run_task(task, claimed_at=now)
        return True

    def run_loop(self, stop_event: threading.Event) -> None:
        with ThreadPoolExecutor(
            max_workers=self.max_concurrency,
            thread_name_prefix=f'{self.worker_id}-slot',
        ) as executor:
            while not stop_event.is_set():
                self._lease_tracker.reap_completed_futures()
                self._lease_tracker.renew_active_leases(now=datetime.now())
                available_slots = self.max_concurrency - self._lease_tracker.active_count
                claimed_count = 0

                if available_slots > 0:
                    now = datetime.now()
                    self._recover_expired_tasks(now=now)
                    for _ in range(available_slots):
                        task = self.dispatcher.claim_next(
                            worker_id=self.worker_id,
                            now=datetime.now(),
                            lease_seconds=self.lease_seconds,
                        )
                        if not task:
                            break
                        submitted_at = datetime.now()
                        future = executor.submit(self.task_runner.run_task, task, submitted_at)
                        self._lease_tracker.track(future, task_id=task.id, now=submitted_at)
                        claimed_count += 1

                if claimed_count:
                    continue
                if self._lease_tracker.active_count:
                    stop_event.wait(0.05)
                    continue
                stop_event.wait(self.poll_interval_seconds)

            self._lease_tracker.reap_completed_futures()

    def _recover_expired_tasks(self, *, now: datetime) -> int:
        return self.task_runner.recover_expired_tasks(now=now)
