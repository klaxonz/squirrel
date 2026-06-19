from __future__ import annotations

from datetime import datetime, timedelta

from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus

from ._intervals import build_retry_delay, build_success_delay, get_mode_interval


def complete_success_state(
    state: SubscriptionSyncState,
    *,
    now: datetime,
    videos_found: int,
    next_sync_at: datetime | None,
) -> datetime | None:
    started_at = state.locked_at or state.last_sync_at
    if state.sync_mode == SyncMode.FULL.value:
        state.gap_suspicion_score = 0
        state.gap_suspicion_reason = None
        state.last_gap_detected_at = None
        state.head_anchor_missing_count = 0
    state.sync_status = SyncStatus.SUCCESS.value
    state.last_sync_at = now
    state.last_success_at = now
    clear_queue_lock(state)
    state.failure_count = 0
    state.last_error = None
    state.idle_sync_count = 0 if videos_found > 0 else state.idle_sync_count + 1
    state.next_sync_at = next_sync_at or (
        now + build_success_delay(state.sync_mode, state.idle_sync_count, videos_found)
    )
    state.version += 1
    return started_at


def continue_full_batch_state(
    state: SubscriptionSyncState,
    *,
    now: datetime,
    cursor_payload: dict | None,
    latest_video_url: str | None,
) -> None:
    state.sync_status = SyncStatus.SUCCESS.value
    state.cursor_payload = cursor_payload or {}
    if latest_video_url and not state.last_seen_video_url:
        state.last_seen_video_url = latest_video_url
    state.last_sync_at = now
    clear_queue_lock(state)
    state.failure_count = 0
    state.idle_sync_count = 0
    state.last_error = None
    state.next_sync_at = now
    state.version += 1


def mark_feed_completed_with_pending_state(
    state: SubscriptionSyncState,
    *,
    now: datetime,
    cursor_payload: dict | None,
    latest_video_url: str | None,
) -> None:
    update_cursor(state, cursor_payload=cursor_payload, latest_video_url=latest_video_url)
    state.sync_status = SyncStatus.RUNNING.value
    state.last_sync_at = now
    clear_queue_lock(state)
    state.failure_count = 0
    state.last_error = None
    state.version += 1


def update_cursor(
    state: SubscriptionSyncState,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
) -> None:
    if cursor_payload is not None:
        state.cursor_payload = cursor_payload
    if latest_video_url:
        state.last_seen_video_url = latest_video_url


def mark_skipped_state(
    state: SubscriptionSyncState,
    *,
    now: datetime,
    next_sync_at: datetime | None,
) -> None:
    state.sync_status = SyncStatus.SUCCESS.value
    state.last_sync_at = now
    state.last_error = None
    clear_queue_lock(state)
    state.failure_count = 0
    state.next_sync_at = next_sync_at or (now + get_mode_interval(state.sync_mode))
    state.version += 1


def mark_failed_state(
    state: SubscriptionSyncState,
    *,
    now: datetime,
    error_message: str,
) -> datetime | None:
    started_at = state.locked_at
    state.failure_count += 1
    state.sync_status = SyncStatus.FAILED.value
    state.last_sync_at = now
    state.last_error = error_message
    clear_queue_lock(state)
    state.idle_sync_count = 0
    state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
    state.version += 1
    return started_at


def defer_state(
    state: SubscriptionSyncState,
    *,
    now: datetime,
    delay: timedelta,
    error_message: str | None,
) -> None:
    state.sync_status = SyncStatus.SUCCESS.value
    state.last_sync_at = now
    state.last_error = error_message
    clear_queue_lock(state)
    state.idle_sync_count = 0
    state.next_sync_at = now + delay
    state.version += 1


def decrement_pending_count(state: SubscriptionSyncState, count: int) -> None:
    state.pending_video_count = max(0, state.pending_video_count - count)
    state.version += 1


def clear_queue_lock(state: SubscriptionSyncState) -> None:
    state.queue_token = None
    state.queued_at = None
    state.locked_at = None
