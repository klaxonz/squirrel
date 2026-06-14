from __future__ import annotations

from domains.subscription.application.services.core.sync.run_service import SyncEventType, SyncRunStatus
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent


def resolve_status(event: SubscriptionSyncEvent) -> str:
    if event.event_status:
        return event.event_status
    mapping = {
        SyncEventType.RUN_CREATED: SyncRunStatus.CREATED,
        SyncEventType.QUEUED: SyncRunStatus.QUEUED,
        SyncEventType.CLAIMED: SyncRunStatus.RUNNING,
        SyncEventType.STARTED: SyncRunStatus.RUNNING,
        SyncEventType.COMPLETED: SyncRunStatus.SUCCESS,
        SyncEventType.FAILED: SyncRunStatus.FAILED,
        SyncEventType.DEFERRED: SyncRunStatus.DEFERRED,
        SyncEventType.TIMEOUT_RECOVERED: SyncRunStatus.TIMEOUT,
        SyncEventType.STALE_RUNNING_RECOVERED: SyncRunStatus.TIMEOUT,
        SyncEventType.STALE_QUEUED_RECOVERED: SyncRunStatus.FAILED,
    }
    return mapping.get(event.event_type, SyncRunStatus.RUNNING)
