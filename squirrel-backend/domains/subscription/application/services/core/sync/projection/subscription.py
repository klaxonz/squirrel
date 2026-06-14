from __future__ import annotations

from domains.subscription.application.services.core.sync.projection.payload import (
    payload_datetime,
    payload_int,
    payload_text,
)
from domains.subscription.application.services.core.sync.projection.status import resolve_status
from domains.subscription.application.services.core.sync.run_service import SyncEventType, SyncRunStatus
from domains.subscription.domain.models.subscription_sync_event import SubscriptionSyncEvent
from domains.subscription.domain.models.subscription_sync_subscription_projection import (
    SubscriptionSyncSubscriptionProjection,
)


def apply_subscription_projection(
    projection: SubscriptionSyncSubscriptionProjection,
    event: SubscriptionSyncEvent,
) -> None:
    incoming_status = resolve_status(event)
    if projection.latest_run_id == event.stream_id:
        if event.seq_no <= projection.last_event_seq_no:
            return
    elif projection.latest_run_id:
        if event.event_type != SyncEventType.RUN_CREATED:
            return
        if projection.current_status in {SyncRunStatus.CREATED, SyncRunStatus.QUEUED, SyncRunStatus.RUNNING} and incoming_status in {
            SyncRunStatus.SUCCESS,
            SyncRunStatus.FAILED,
            SyncRunStatus.DEFERRED,
            SyncRunStatus.TIMEOUT,
        }:
            return
    payload = event.payload or {}
    projection.latest_run_id = event.stream_id
    projection.current_status = incoming_status
    projection.current_phase = event.event_phase or projection.current_phase
    projection.last_event_seq_no = event.seq_no
    projection.updated_at = event.occurred_at
    projection.pending_video_count = payload_int(payload, 'pending_video_count', projection.pending_video_count)

    next_sync_at = payload_datetime(payload, 'next_sync_at')
    if next_sync_at:
        projection.next_sync_at = next_sync_at

    if event.event_type in {
        SyncEventType.COMPLETED,
        SyncEventType.FAILED,
        SyncEventType.DEFERRED,
        SyncEventType.TIMEOUT_RECOVERED,
        SyncEventType.STALE_RUNNING_RECOVERED,
        SyncEventType.STALE_QUEUED_RECOVERED,
    }:
        projection.last_sync_at = event.occurred_at

    if event.event_type == SyncEventType.COMPLETED:
        projection.last_success_at = event.occurred_at
        projection.last_error_message = None
        projection.failure_streak = 0
    elif event.event_type in {
        SyncEventType.FAILED,
        SyncEventType.TIMEOUT_RECOVERED,
        SyncEventType.STALE_RUNNING_RECOVERED,
        SyncEventType.STALE_QUEUED_RECOVERED,
    }:
        projection.last_error_message = payload_text(payload, 'error_message', event.message)
        projection.failure_streak += 1
    elif event.event_type == SyncEventType.DEFERRED:
        projection.last_error_message = payload_text(payload, 'error_message', event.message)
