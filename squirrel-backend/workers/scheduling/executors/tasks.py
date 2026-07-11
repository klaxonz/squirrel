from __future__ import annotations

import logging
from datetime import datetime

from domains.subscription.application.services.core.update.task_progress_service import (
    SubscriptionSyncTaskProgressService,
)
from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
    execute_subscription_sync_task,
)
from domains.subscription.application.services.crawl.executors.video_extract_executor import execute_video_extract_task
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import is_subscription_sync_task_type
from domains.video.application.services.extraction.progress_service import VideoExtractionProgressService
from domains.video.interfaces.dto.video_dto import VideoExtractDto

logger = logging.getLogger(__name__)


class CrawlWorkerTaskRunner:
    def __init__(
        self,
        *,
        worker_id: str,
        retry_delay_seconds: int,
        subscription_task_progress: SubscriptionSyncTaskProgressService | None = None,
        video_extraction_progress: VideoExtractionProgressService | None = None,
    ) -> None:
        self.worker_id = worker_id
        self.retry_delay_seconds = retry_delay_seconds
        self.subscription_task_progress = subscription_task_progress or SubscriptionSyncTaskProgressService()
        self.video_extraction_progress = video_extraction_progress or VideoExtractionProgressService()

    def run_task(self, task, claimed_at: datetime) -> None:
        try:
            crawl_task_service.start_task(task_id=task.id, worker_id=self.worker_id, now=claimed_at)
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
        return len(recovered_tasks)

    def execute_task(self, task) -> None:
        if task.task_type == 'video_extract':
            execute_video_extract_task(task)
            return
        if is_subscription_sync_task_type(task.task_type):
            execute_subscription_sync_task(task)
            return
        raise ValueError(f'Unsupported crawl task type: {task.task_type}')

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
            self._record_video_extract_terminal_if_needed(retried_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task retry because lease is no longer owned: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )

    def _complete_task(self, task) -> None:
        try:
            completed_task = crawl_task_service.complete_task(task_id=task.id, worker_id=self.worker_id, now=datetime.now())
            self._record_video_extract_terminal_if_needed(completed_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task completion because lease is no longer owned: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )

    def cancel_task(self, task, *, reason: str = 'cancelled', now: datetime | None = None) -> None:
        try:
            cancelled_task = crawl_task_service.cancel_task(task_id=task.id, now=now or datetime.now(), reason=reason)
            self._record_video_extract_terminal_if_needed(cancelled_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task cancellation because task is no longer available: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )

    def _record_video_extract_terminal_if_needed(self, task) -> None:
        if task.task_type != 'video_extract':
            return

        match task.status:
            case CrawlTaskStatus.SUCCEEDED.value:
                self._record_video_extract_terminal(task, succeeded=True)
            case CrawlTaskStatus.DEAD.value | CrawlTaskStatus.CANCELLED.value:
                self._record_video_extract_terminal(task, succeeded=False)

    def _record_video_extract_terminal(self, task, *, succeeded: bool) -> None:
        try:
            params = VideoExtractDto.model_validate(task.payload or {})
        except (TypeError, ValueError, AttributeError) as exc:
            logger.warning(
                'Skip video extraction progress update for invalid payload: task_id=%s error=%s',
                task.id,
                exc,
            )
            return
        self.video_extraction_progress.record_terminal(params, succeeded=succeeded)
