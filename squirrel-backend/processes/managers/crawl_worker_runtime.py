from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
import logging
import threading
from datetime import datetime

from core.config import settings
from services.crawl_dispatcher.service import CrawlDispatcherService
from services.crawl_executors.subscription_sync_executor import execute_subscription_sync_task
from services.crawl_executors.video_extract_executor import execute_video_extract_task
from services.crawl_tasks import service as crawl_task_service

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
    ):
        self.dispatcher = dispatcher or CrawlDispatcherService()
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds or settings.CRAWL_WORKER_LEASE_SECONDS
        self.retry_delay_seconds = retry_delay_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_concurrency = max(1, max_concurrency or settings.CRAWL_SLOTS_PER_PROCESS)
        self._futures: set[Future] = set()

    def run_once(self) -> bool:
        now = datetime.now()
        crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=self.retry_delay_seconds)
        task = self.dispatcher.claim_next(worker_id=self.worker_id, now=now, lease_seconds=self.lease_seconds)
        if not task:
            return False

        self._run_task(task, claimed_at=now)
        return True

    def run_loop(self, stop_event: threading.Event) -> None:
        with ThreadPoolExecutor(
            max_workers=self.max_concurrency,
            thread_name_prefix=f'{self.worker_id}-slot',
        ) as executor:
            while not stop_event.is_set():
                self._reap_completed_futures()
                available_slots = self.max_concurrency - len(self._futures)
                claimed_count = 0

                if available_slots > 0:
                    now = datetime.now()
                    crawl_task_service.recover_expired_tasks(now=now, retry_delay_seconds=self.retry_delay_seconds)
                    for _ in range(available_slots):
                        task = self.dispatcher.claim_next(
                            worker_id=self.worker_id,
                            now=datetime.now(),
                            lease_seconds=self.lease_seconds,
                        )
                        if not task:
                            break
                        future = executor.submit(self._run_task, task, datetime.now())
                        self._futures.add(future)
                        claimed_count += 1

                if claimed_count:
                    continue
                if self._futures:
                    stop_event.wait(0.05)
                    continue
                stop_event.wait(self.poll_interval_seconds)

            self._reap_completed_futures()

    def _execute_task(self, task) -> None:
        if task.task_type == 'video_extract':
            execute_video_extract_task(task)
            return
        if task.task_type == 'subscription_sync':
            execute_subscription_sync_task(task)
            return
        raise ValueError(f'Unsupported crawl task type: {task.task_type}')

    def _run_task(self, task, claimed_at: datetime) -> None:
        try:
            crawl_task_service.start_task(task_id=task.id, worker_id=self.worker_id, now=claimed_at)
            self._execute_task(task)
            crawl_task_service.complete_task(task_id=task.id, worker_id=self.worker_id, now=datetime.now())
        except Exception as exc:
            logger.exception("Crawl worker execution failed task_id=%s task_type=%s", task.id, task.task_type)
            crawl_task_service.retry_task(
                task_id=task.id,
                worker_id=self.worker_id,
                error_message=str(exc),
                error_type=type(exc).__name__,
                now=datetime.now(),
                delay_seconds=self.retry_delay_seconds,
            )

    def _reap_completed_futures(self) -> None:
        completed = {future for future in self._futures if future.done()}
        for future in completed:
            future.result()
        self._futures.difference_update(completed)
