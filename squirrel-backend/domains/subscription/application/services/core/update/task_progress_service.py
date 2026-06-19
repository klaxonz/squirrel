from datetime import datetime

from domains.subscription.application.services.core.sync.lifecycle import subscription_sync_lifecycle
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import is_subscription_sync_task_type
from domains.subscription.domain.models.crawl_task import CrawlTask


class SubscriptionSyncTaskProgressService:
    def __init__(self, lifecycle=None):
        self._lifecycle = lifecycle or subscription_sync_lifecycle

    def record_retry_transition(
        self,
        task: CrawlTask,
        *,
        now: datetime,
        error_message: str | None,
    ) -> None:
        if not is_subscription_sync_task_type(task.task_type):
            return

        payload = task.payload or {}
        sync_state_id = payload.get("sync_state_id")
        if sync_state_id in (None, ""):
            return

        try:
            resolved_sync_state_id = int(sync_state_id)
        except (TypeError, ValueError):
            return

        retryable = task.status == CrawlTaskStatus.RETRY_WAIT.value
        self._lifecycle.record_task_retry_transition(
            resolved_sync_state_id,
            payload.get("queue_token"),
            now=now,
            retryable=retryable,
            error_message=error_message,
            run_id=payload.get("run_id"),
            request_id=payload.get("request_id"),
            trace_id=payload.get("trace_id"),
            trigger=payload.get("trigger"),
        )


subscription_sync_task_progress_service = SubscriptionSyncTaskProgressService()
record_retry_transition = subscription_sync_task_progress_service.record_retry_transition
