from __future__ import annotations

import logging
from datetime import datetime

from domains.subscription.application.services.core.update.task_progress_service import (
    SubscriptionSyncTaskProgressService,
)
from domains.subscription.application.services.crawl.executors.subscription_import_executor import (
    execute_subscription_import_task,
)
from domains.subscription.application.services.crawl.executors.subscription_sync_executor import (
    CrawlExecutorService as SubscriptionSyncExecutor,
)
from domains.subscription.application.services.crawl.executors.video_extract_executor import execute_video_extract_task
from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.application.services.crawl.tasks.errors import CrawlTaskNotFoundError, CrawlTaskOwnershipError
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import is_subscription_sync_task_type
from domains.video.application.services.extraction.progress_service import VideoExtractionProgressService
from domains.video.interfaces.dto.video_dto import VideoExtractDto
from shared_kernel.domain.exceptions import DomainError

logger = logging.getLogger(__name__)


class CrawlWorkerTaskRunner:
    def __init__(
        self,
        *,
        worker_id: str,
        retry_delay_seconds: int,
        subscription_task_progress: SubscriptionSyncTaskProgressService,
        video_extraction_progress: VideoExtractionProgressService,
        subscription_sync_executor: SubscriptionSyncExecutor,
    ) -> None:
        self.worker_id = worker_id
        self.retry_delay_seconds = retry_delay_seconds
        self.subscription_task_progress = subscription_task_progress
        self.video_extraction_progress = video_extraction_progress
        self.subscription_sync_executor = subscription_sync_executor

    def run_task(self, task, claimed_at: datetime) -> None:
        try:
            ownership = {
                'task_id': task.id,
                'worker_id': self.worker_id,
            }
            if task.lease_token:
                ownership['lease_token'] = task.lease_token
            crawl_task_service.start_task(
                **ownership,
            )
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

    def recover_expired_tasks(self, *, now: datetime | None = None) -> int:
        recovery_kwargs = {'retry_delay_seconds': self.retry_delay_seconds}
        if now is not None:
            recovery_kwargs['now'] = now
        recovered_tasks = crawl_task_service.recover_expired_tasks(**recovery_kwargs)
        for recovered in recovered_tasks:
            task = getattr(recovered, 'task', recovered)
            execution_token = getattr(recovered, 'execution_token', task.lease_token)
            transition_time = getattr(recovered, 'recovered_at', None) or now or datetime.now()
            progress_kwargs = {'now': transition_time, 'error_message': task.last_error}
            if execution_token is not None:
                progress_kwargs['execution_token'] = execution_token
            self.subscription_task_progress.record_retry_transition(task, **progress_kwargs)
            self._record_video_extract_terminal_if_needed(task)
        return len(recovered_tasks)

    def execute_task(self, task) -> None:
        if task.task_type == 'video_extract':
            execute_video_extract_task(task)
            return
        if is_subscription_sync_task_type(task.task_type):
            self.subscription_sync_executor.execute_subscription_sync_task(task)
            return
        if task.task_type == 'subscription_import':
            execute_subscription_import_task(task)
            return
        raise ValueError(f'Unsupported crawl task type: {task.task_type}')

    def _retry_task(self, task, exc: Exception) -> None:
        try:
            retry_now = datetime.now()
            execution_token = task.lease_token
            default_retryable = not isinstance(exc, (DomainError, ValueError, TypeError, AttributeError, KeyError))
            retryable = bool(getattr(exc, 'retryable', default_retryable))
            error_type = str(getattr(exc, 'error_type', None) or type(exc).__name__)
            retry_kwargs = {
                'task_id': task.id,
                'worker_id': self.worker_id,
                'error_message': str(exc),
                'error_type': error_type,
                'delay_seconds': self._retry_delay_for(task, exc),
            }
            if task.lease_token:
                retry_kwargs['lease_token'] = task.lease_token
            if not retryable:
                retry_kwargs['retryable'] = False
            retried_task = crawl_task_service.retry_task(
                **retry_kwargs,
            )
            progress_kwargs = {'now': retry_now, 'error_message': str(exc)}
            if execution_token is not None:
                progress_kwargs['execution_token'] = execution_token
            self.subscription_task_progress.record_retry_transition(retried_task, **progress_kwargs)
            self._record_video_extract_terminal_if_needed(retried_task)
        except (CrawlTaskOwnershipError, CrawlTaskNotFoundError):
            logger.warning(
                'Skip crawl task retry because lease is no longer owned: task_id=%s worker_id=%s',
                task.id,
                self.worker_id,
            )

    def _complete_task(self, task) -> None:
        try:
            complete_kwargs = {
                'task_id': task.id,
                'worker_id': self.worker_id,
            }
            if task.lease_token:
                complete_kwargs['lease_token'] = task.lease_token
            completed_task = crawl_task_service.complete_task(
                **complete_kwargs,
            )
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

    def _retry_delay_for(self, task, exc: Exception) -> int:
        """Return capped exponential backoff with deterministic per-task jitter."""
        base = max(1, int(self.retry_delay_seconds))
        exponential = base * (2 ** max(0, int(task.attempt or 0)))
        jitter_percent = ((int(task.id or 0) * 37 + int(task.attempt or 0) * 17) % 21) / 100
        delay = min(3600, max(1, int(exponential * (1 + jitter_percent))))
        retry_after = getattr(exc, 'retry_after_seconds', None)
        if retry_after is not None:
            delay = max(delay, min(3600, max(1, int(retry_after))))
        return delay
