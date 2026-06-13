from __future__ import annotations

import logging
from datetime import datetime

import services.video.extraction_projection.service as video_extraction_projection_service
from services.crawl.executors.subscription_sync_executor import execute_subscription_sync_task
from services.crawl.executors.video_extract_executor import execute_video_extract_task
from services.crawl.tasks import service as crawl_task_service
from services.crawl.tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError
from services.crawl.tasks.task_types import is_subscription_sync_task_type
from services.subscription.update.task_progress_service import SubscriptionSyncTaskProgressService

logger = logging.getLogger(__name__)


class CrawlWorkerTaskRunner:
    def __init__(
        self,
        *,
        worker_id: str,
        retry_delay_seconds: int,
        subscription_task_progress: SubscriptionSyncTaskProgressService | None = None,
        video_projection_service=None,
    ) -> None:
        self.worker_id = worker_id
        self.retry_delay_seconds = retry_delay_seconds
        self.subscription_task_progress = subscription_task_progress or SubscriptionSyncTaskProgressService()
        self.video_projection_service = video_projection_service or video_extraction_projection_service

    def run_task(self, task, claimed_at: datetime) -> None:
        try:
            started_task = crawl_task_service.start_task(task_id=task.id, worker_id=self.worker_id, now=claimed_at)
            self.refresh_video_projection(started_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task start because lease is no longer owned: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )
            return

        try:
            self.execute_task(task)
        except Exception as exc:  # task boundary -- prevent single failure from crashing scheduler
            logger.exception('Crawl worker execution failed task_id=%s task_type=%s', task.id, task.task_type)
            self._retry_task(task, exc)
            return

        self._complete_task(task)

    def recover_expired_tasks(self, *, now: datetime) -> int:
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
            self.refresh_video_projection(task)
        return len(recovered_tasks)

    def execute_task(self, task) -> None:
        if task.task_type == 'video_extract':
            execute_video_extract_task(task)
            return
        if is_subscription_sync_task_type(task.task_type):
            execute_subscription_sync_task(task)
            return
        raise ValueError(f'Unsupported crawl task type: {task.task_type}')

    def refresh_video_projection(self, task) -> None:
        self.video_projection_service.refresh_projection_for_task(task)

    def _retry_task(self, task, exc: Exception) -> None:
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
            self.refresh_video_projection(retried_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task retry because lease is no longer owned: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )

    def _complete_task(self, task) -> None:
        try:
            completed_task = crawl_task_service.complete_task(task_id=task.id, worker_id=self.worker_id, now=datetime.now())
            self.refresh_video_projection(completed_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task completion because lease is no longer owned: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )
