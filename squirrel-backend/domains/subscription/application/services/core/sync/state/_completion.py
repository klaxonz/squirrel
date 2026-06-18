from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncStatus

from ._completion_transitions import (
    complete_success_state,
    continue_full_batch_state,
    decrement_pending_count,
    defer_state,
    mark_failed_state,
    mark_feed_completed_with_pending_state,
    mark_skipped_state,
    update_cursor,
)
from ._stale import _can_complete_drained_state
from .session import get_session


def _complete_sync_success_in_session(
    session: Session,
    *,
    state: SubscriptionSyncState,
    videos_found: int = 0,
    next_sync_at: datetime | None = None,
) -> SubscriptionSyncState:
    now = datetime.now()
    complete_success_state(
        state,
        now=now,
        videos_found=videos_found,
        next_sync_at=next_sync_at,
    )
    return state


def continue_full_sync_batch(
    sync_state_id: int,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
    videos_found: int = 0,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        continue_full_batch_state(
            state,
            now=now,
            cursor_payload=cursor_payload,
            latest_video_url=latest_video_url,
        )
        return state


def mark_sync_success(
    sync_state_id: int,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
    videos_found: int = 0,
    next_sync_at: datetime | None = None,
) -> SubscriptionSyncState | None:
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        now = datetime.now()

        if state.pending_video_count > 0:
            mark_feed_completed_with_pending_state(
                state,
                now=now,
                cursor_payload=cursor_payload,
                latest_video_url=latest_video_url,
            )
            return state

        update_cursor(state, cursor_payload=cursor_payload, latest_video_url=latest_video_url)
        _complete_sync_success_in_session(
            session,
            state=state,
            videos_found=videos_found,
            next_sync_at=next_sync_at,
        )
        return state


def mark_sync_skipped(
    sync_state_id: int,
    *,
    next_sync_at: datetime | None = None,
    reason: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        mark_skipped_state(state, now=now, next_sync_at=next_sync_at)
        return state


def mark_sync_failed(
    sync_state_id: int,
    error_message: str,
    *,
    error_type: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        mark_failed_state(state, now=now, error_message=error_message)
        return state


def defer_sync_state(
    sync_state_id: int,
    *,
    delay: timedelta,
    error_message: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        defer_state(state, now=now, delay=delay, error_message=error_message)
        return state


def decrement_pending_video_count(
    sync_state_id: int | None,
    count: int = 1,
    *,
    allow_completion: bool = True,
) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        decrement_pending_count(state, count)
        if (
            allow_completion
            and state.pending_video_count == 0
            and state.sync_status == SyncStatus.RUNNING.value
            and state.locked_at is None
            and _can_complete_drained_state(state.id)
        ):
            _complete_sync_success_in_session(session, state=state)
