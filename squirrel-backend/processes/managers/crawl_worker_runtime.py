from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime

from core.config import settings
from services import video_extraction_projection_service
from services.crawl_dispatcher.service import CrawlDispatcherService
from services.crawl_executors.subscription_sync_executor import execute_subscription_sync_task
from services.crawl_executors.video_extract_executor import execute_video_extract_task
from services.crawl_tasks import service as crawl_task_service
from services.crawl_tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError
from services.crawl_tasks.task_types import is_subscription_sync_task_type
from services.subscription_update.task_progress_service import SubscriptionSyncTaskProgressService

logger = logging.getLogger(__name__)


@dataclass
class _ActiveTaskLease:
    task_id: int
    last_renewed_at: datetime


class CrawlWorkerRuntime:
    def __init__(
        self,
        *,
        dispatcher: CrawlDispatcherService | None = None,
        worker_id: str = "crawl-worker-1",
        lease_seconds: int | None = None,
        retry_delay_seconds: int = 30,
        poll_interval_seconds: float = 1.0,
        max_concurrency: int | None = None,
        subscription_task_progress: SubscriptionSyncTaskProgressService | None = None,
        video_projection_service=None,
    ):
        self.dispatcher = dispatcher or CrawlDispatcherService()
        self.worker_id = worker_id
        self.lease_seconds = lease_seconds or settings.CRAWL_WORKER_LEASE_SECONDS
        self.retry_delay_seconds = retry_delay_seconds
        self.poll_interval_seconds = poll_interval_seconds
        self.max_concurrency = max(1, max_concurrency or settings.CRAWL_SLOTS_PER_PROCESS)
        self.subscription_task_progress = subscription_task_progress or SubscriptionSyncTaskProgressService()
        self.video_projection_service = video_projection_service or video_extraction_projection_service
        self._futures: set[Future] = set()
        self._active_leases: dict[Future, _ActiveTaskLease] = {}

    def run_once(self) -> bool:
        now = datetime.now()
        self._recover_expired_tasks(now=now)
        task = self.dispatcher.claim_next(worker_id=self.worker_id, now=now, lease_seconds=self.lease_seconds)
        if not task:
            return False

        self._refresh_video_projection(task)
        self._run_task(task, claimed_at=now)
        return True

    def run_loop(self, stop_event: threading.Event) -> None:
        with ThreadPoolExecutor(
            max_workers=self.max_concurrency,
            thread_name_prefix=f"{self.worker_id}-slot",
        ) as executor:
            while not stop_event.is_set():
                self._reap_completed_futures()
                self._renew_active_leases(now=datetime.now())
                available_slots = self.max_concurrency - len(self._futures)
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
                        self._refresh_video_projection(task)
                        future = executor.submit(self._run_task, task, datetime.now())
                        self._futures.add(future)
                        self._active_leases[future] = _ActiveTaskLease(task_id=task.id, last_renewed_at=datetime.now())
                        claimed_count += 1

                if claimed_count:
                    continue
                if self._futures:
                    stop_event.wait(0.05)
                    continue
                stop_event.wait(self.poll_interval_seconds)

            self._reap_completed_futures()

    def _execute_task(self, task) -> None:
        if task.task_type == "video_extract":
            execute_video_extract_task(task)
            return
        if is_subscription_sync_task_type(task.task_type):
            execute_subscription_sync_task(task)
            return
        raise ValueError(f"Unsupported crawl task type: {task.task_type}")

    def _run_task(self, task, claimed_at: datetime) -> None:
        try:
            started_task = crawl_task_service.start_task(task_id=task.id, worker_id=self.worker_id, now=claimed_at)
            self._refresh_video_projection(started_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                "Skip crawl task start because lease is no longer owned: task_id=%s worker_id=%s",
                task.id,
                self.worker_id,
            )
            return

        try:
            self._execute_task(task)
        except Exception as exc:  # task boundary -- prevent single failure from crashing scheduler
            logger.exception("Crawl worker execution failed task_id=%s task_type=%s", task.id, task.task_type)
            try:
                retry_now = datetime.now()
                retried_task = crawl_task_service.retry_task(
                    task_id=task.id,
                    worker_id=self.worker_id,
                    error_message=str(exc),
                    error_type=type(exc).__name__,
                    now=retry_now,
                    delay_seconds=self.retry_delay_seconds,
                )
                self.subscription_task_progress.record_retry_transition(
                    retried_task,
                    now=retry_now,
                    error_message=str(exc),
                )
                self._refresh_video_projection(retried_task)
            except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
                logger.warning(
                    "Skip crawl task retry because lease is no longer owned: task_id=%s worker_id=%s",
                    task.id,
                    self.worker_id,
                )
            return

        try:
            completed_task = crawl_task_service.complete_task(task_id=task.id, worker_id=self.worker_id, now=datetime.now())
            self._refresh_video_projection(completed_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                "Skip crawl task completion because lease is no longer owned: task_id=%s worker_id=%s",
                task.id,
                self.worker_id,
            )

    def _reap_completed_futures(self) -> None:
        completed = {future for future in self._futures if future.done()}
        for future in completed:
            future.result()
            self._active_leases.pop(future, None)
        self._futures.difference_update(completed)

    def _renew_active_leases(self, *, now: datetime) -> None:
        for future in tuple(self._futures):
            if future.done():
                continue
            lease = self._active_leases.get(future)
            if lease is None:
                continue
            renew_after = max(0.25, self.lease_seconds / 3)
            if (now - lease.last_renewed_at).total_seconds() < renew_after:
                continue
            try:
                crawl_task_service.renew_task_lease(
                    task_id=lease.task_id,
                    worker_id=self.worker_id,
                    now=now,
                    lease_seconds=self.lease_seconds,
                )
            except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
                logger.warning(
                    "Stop renewing crawl task lease because ownership is lost: task_id=%s worker_id=%s",
                    lease.task_id,
                    self.worker_id,
                )
                self._active_leases.pop(future, None)
                continue
            lease.last_renewed_at = now

    def _recover_expired_tasks(self, *, now: datetime) -> int:
        recovered_tasks = crawl_task_service.recover_expired_tasks(
            now=now,
            retry_delay_seconds=self.retry_delay_seconds,
        )
        for task in recovered_tasks:
            self.subscription_task_progress.record_retry_transition(
                task,
                now=now,
                error_message=task.last_error,
            )
            self._refresh_video_projection(task)
        return len(recovered_tasks)

    def _refresh_video_projection(self, task) -> None:
        self.video_projection_service.refresh_projection_for_task(task)
