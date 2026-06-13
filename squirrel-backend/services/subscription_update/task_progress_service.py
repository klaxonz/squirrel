from datetime import datetime

from models.crawl_task import CrawlTask
from services import subscription_sync_state_service
from services.crawl_tasks.models import CrawlTaskStatus
from services.crawl_tasks.task_types import is_subscription_sync_task_type


class SubscriptionSyncTaskProgressService:
    def __init__(self, sync_state_service=None):
        self._sync_state_service = sync_state_service or subscription_sync_state_service

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
        self._sync_state_service.reconcile_task_retry_state(
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


_default = SubscriptionSyncTaskProgressService()
record_retry_transition = _default.record_retry_transition
