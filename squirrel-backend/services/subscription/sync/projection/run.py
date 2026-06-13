from __future__ import annotations

from models.subscription_sync_event import SubscriptionSyncEvent
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from services.subscription.sync.projection.payload import payload_int, payload_text
from services.subscription.sync.projection.status import resolve_status
from services.subscription.sync.run_service import SyncEventType


def apply_run_projection(projection: SubscriptionSyncRunProjection, event: SubscriptionSyncEvent) -> None:
    if event.seq_no <= projection.last_event_seq_no:
        return
    payload = event.payload or {}
    projection.sync_state_id = event.sync_state_id
    projection.site = event.site
    projection.sync_mode = event.sync_mode
    projection.trigger = event.trigger
    projection.request_id = event.request_id
    projection.trace_id = event.trace_id
    projection.status = resolve_status(event)
    projection.current_phase = event.event_phase or projection.current_phase
    projection.last_event_seq_no = event.seq_no
    projection.last_event_at = event.occurred_at
    projection.updated_at = event.occurred_at

    if event.event_type == SyncEventType.QUEUED and not projection.queued_at:
        projection.queued_at = event.occurred_at
    if event.event_type in {SyncEventType.CLAIMED, SyncEventType.STARTED} and not projection.started_at:
        projection.started_at = event.occurred_at
    if event.event_type in {
        SyncEventType.COMPLETED,
        SyncEventType.FAILED,
        SyncEventType.DEFERRED,
        SyncEventType.TIMEOUT_RECOVERED,
        SyncEventType.STALE_RUNNING_RECOVERED,
        SyncEventType.STALE_QUEUED_RECOVERED,
    }:
        projection.finished_at = event.occurred_at

    if projection.started_at and projection.finished_at:
        projection.duration_ms = max(0, int((projection.finished_at - projection.started_at).total_seconds() * 1000))

    if 'failure_count' in payload:
        projection.failure_count = payload_int(payload, 'failure_count', projection.failure_count)
    elif event.event_type in {
        SyncEventType.FAILED,
        SyncEventType.TIMEOUT_RECOVERED,
        SyncEventType.STALE_RUNNING_RECOVERED,
        SyncEventType.STALE_QUEUED_RECOVERED,
    }:
        projection.failure_count += 1

    projection.pending_video_count = payload_int(payload, 'pending_video_count', projection.pending_video_count)
    projection.error_type = payload_text(payload, 'error_type', projection.error_type)
    projection.error_message = payload_text(payload, 'error_message', projection.error_message)
    apply_counter_payload(projection, event)


def apply_counter_payload(projection: SubscriptionSyncRunProjection, event: SubscriptionSyncEvent) -> None:
    counter_by_event_type = {
        SyncEventType.VIDEO_FOUND: 'videos_found',
        SyncEventType.VIDEO_ENQUEUED: 'videos_enqueued',
        SyncEventType.VIDEO_EXTRACTED: 'videos_extracted',
        SyncEventType.VIDEO_SKIPPED: 'videos_skipped',
    }
    counter_name = counter_by_event_type.get(event.event_type)
    if not counter_name:
        return

    payload = event.payload or {}
    delta_key = f'{counter_name}_delta'
    if delta_key in payload:
        current_value = getattr(projection, counter_name)
        setattr(projection, counter_name, max(0, current_value + payload_int(payload, delta_key)))
        return

    if counter_name in payload:
        current_value = getattr(projection, counter_name)
        next_value = payload_int(payload, counter_name, current_value)
        setattr(projection, counter_name, max(current_value, next_value))
