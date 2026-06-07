from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus
from services.subscription_sync_run_service import SyncEventType, SyncPhase, SyncRunStatus

from . import get_session
from ._crud import _get_or_create_sync_state_in_session
from ._events import _append_state_event
from ._intervals import INCREMENTAL_PENDING_THRESHOLD, build_retry_delay, build_success_delay, get_mode_interval
from ._stale import _can_complete_drained_state, _recover_stale_running_state


def deactivate_sync_states(subscription_id: int, *, reason: str = "deactivated") -> int:
    now = datetime.now()
    updated_count = 0

    with get_session() as session:
        states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.subscription_id == subscription_id,
            ),
        ).scalars().all()

        for state in states:
            state.sync_status = SyncStatus.IDLE.value
            state.last_error = reason
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.pending_video_count = 0
            state.last_sync_at = now
            state.version += 1
            updated_count += 1

    return updated_count


def prepare_sync_state_for_enqueue(
    subscription_id: int,
    url: str | None,
    mode: str,
    *,
    scheduled: bool,
) -> tuple[SubscriptionSyncState | None, str]:
    now = datetime.now()
    with get_session() as session:
        state = _get_or_create_sync_state_in_session(session, subscription_id, mode, url)
        _recover_stale_running_state(state, now)

        if state.sync_status == SyncStatus.RUNNING.value:
            return state, "in_progress"
        if state.sync_status == SyncStatus.QUEUED.value:
            return state, "queued"

        if scheduled and has_incremental_backpressure(state):
            state.sync_status = SyncStatus.SUCCESS.value
            state.last_sync_at = now
            state.last_error = "queue_backpressure"
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.next_sync_at = now + get_mode_interval(state.sync_mode)
            state.version += 1
            return state, "deferred"

        return state, "ready"


def queue_sync_state(sync_state_id: int, queue_token: str) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        session.execute(
            update(SubscriptionSyncState)
            .where(
                SubscriptionSyncState.id == sync_state_id,
                SubscriptionSyncState.sync_status.notin_(
                    [SyncStatus.QUEUED.value, SyncStatus.RUNNING.value],
                ),
            )
            .values(
                sync_status=SyncStatus.QUEUED.value,
                queue_token=queue_token,
                queued_at=now,
                locked_at=None,
                last_error=None,
                version=SubscriptionSyncState.version + 1,
            ),
        )
        return session.execute(
            select(SubscriptionSyncState).where(SubscriptionSyncState.id == sync_state_id),
        ).scalar_one_or_none()


def claim_sync_state(
    sync_state_id: int,
    queue_token: str,
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        result = session.execute(
            update(SubscriptionSyncState)
            .where(
                SubscriptionSyncState.id == sync_state_id,
                SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                SubscriptionSyncState.queue_token == queue_token,
            )
            .values(
                sync_status=SyncStatus.RUNNING.value,
                locked_at=now,
                last_sync_at=now,
                version=SubscriptionSyncState.version + 1,
            ),
        )
        if result.rowcount == 0:
            return None
        state = session.execute(
            select(SubscriptionSyncState).where(SubscriptionSyncState.id == sync_state_id),
        ).scalar_one_or_none()
        if not state:
            return None
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.CLAIMED,
            event_phase=SyncPhase.CLAIMED,
            event_status=SyncRunStatus.RUNNING,
            payload={
                "pending_video_count": state.pending_video_count,
                "queue_token": queue_token,
            },
            occurred_at=now,
        )
        return state


def reconcile_task_retry_state(
    sync_state_id: int | None,
    queue_token: str | None,
    *,
    now: datetime | None = None,
    retryable: bool,
    error_message: str | None = None,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    if not sync_state_id:
        return None

    now = now or datetime.now()
    expected_token = str(queue_token or "").strip() or None

    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None

        current_token = str(state.queue_token or "").strip() or None
        if expected_token and current_token and current_token != expected_token:
            return state

        if retryable:
            if state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
                return state
            state.sync_status = SyncStatus.QUEUED.value
            state.queue_token = expected_token or state.queue_token
            state.queued_at = now
            state.locked_at = None
            state.last_error = error_message
            state.version += 1
            _append_state_event(
                session,
                state=state,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger,
                event_type=SyncEventType.QUEUED,
                event_phase=SyncPhase.QUEUED,
                event_status=SyncRunStatus.QUEUED,
                payload={
                    "queue_token": state.queue_token,
                    "queued_at": state.queued_at,
                    "pending_video_count": state.pending_video_count,
                    "error_message": error_message,
                },
                message=error_message,
                occurred_at=now,
            )
            return state

        if state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
            return state

        state.failure_count += 1
        state.sync_status = SyncStatus.FAILED.value
        state.last_sync_at = now
        state.last_error = error_message or "task_retry_exhausted"
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.FAILED,
            event_phase=SyncPhase.FAILED,
            event_status=SyncRunStatus.FAILED,
            payload={
                "error_message": state.last_error,
                "failure_count": state.failure_count,
                "pending_video_count": state.pending_video_count,
                "next_sync_at": state.next_sync_at,
            },
            message=state.last_error,
            occurred_at=now,
        )
        return state


def _complete_sync_success_in_session(
    session: Session,
    *,
    state: SubscriptionSyncState,
    source_video_count: int | None = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    next_sync_at: datetime | None = None,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState:
    now = datetime.now()
    started_at = state.locked_at or state.last_sync_at
    if state.sync_mode == SyncMode.FULL.value:
        state.gap_suspicion_score = 0
        state.gap_suspicion_reason = None
        state.last_gap_detected_at = None
        state.head_anchor_missing_count = 0
    state.sync_status = SyncStatus.SUCCESS.value
    state.last_sync_at = now
    state.last_success_at = now
    state.queue_token = None
    state.queued_at = None
    state.locked_at = None
    state.failure_count = 0
    state.last_error = None
    state.idle_sync_count = 0 if videos_found > 0 else state.idle_sync_count + 1
    state.next_sync_at = next_sync_at or (now + build_success_delay(state.sync_mode, state.idle_sync_count, videos_found))
    state.version += 1
    _append_state_event(
        session,
        state=state,
        run_id=run_id,
        request_id=request_id,
        trace_id=trace_id,
        trigger=trigger,
        event_type=SyncEventType.COMPLETED,
        event_phase=SyncPhase.COMPLETED,
        event_status=SyncRunStatus.SUCCESS,
        payload={
            "cursor_payload": state.cursor_payload,
            "latest_video_url": state.last_seen_video_url,
            "source_video_count": source_video_count,
            "videos_found": videos_found,
            "videos_enqueued": videos_enqueued,
            "pending_video_count": state.pending_video_count,
            "failure_count": state.failure_count,
            "next_sync_at": state.next_sync_at,
            "duration_ms": int((now - started_at).total_seconds() * 1000) if started_at else 0,
        },
        occurred_at=now,
    )
    return state


def continue_full_sync_batch(
    sync_state_id: int,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
    source_video_count: int | None = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.cursor_payload = cursor_payload or {}
        if latest_video_url and not state.last_seen_video_url:
            state.last_seen_video_url = latest_video_url
        state.last_sync_at = now
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count = 0
        state.idle_sync_count = 0
        state.last_error = None
        state.next_sync_at = now
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.CONTINUED,
            event_phase=SyncPhase.FINALIZING,
            event_status=SyncRunStatus.RUNNING,
            payload={
                "cursor_payload": state.cursor_payload,
                "latest_video_url": latest_video_url,
                "source_video_count": source_video_count,
                "videos_found_delta": videos_found,
                "videos_enqueued_delta": videos_enqueued,
                "pending_video_count": state.pending_video_count,
                "next_sync_at": state.next_sync_at,
                "has_more": True,
            },
            occurred_at=now,
        )
        return state


def mark_sync_success(
    sync_state_id: int,
    *,
    cursor_payload: dict | None,
    latest_video_url: str | None,
    source_video_count: int | None = None,
    videos_found: int = 0,
    videos_enqueued: int = 0,
    next_sync_at: datetime | None = None,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        now = datetime.now()
        if cursor_payload is not None:
            state.cursor_payload = cursor_payload
        if latest_video_url:
            state.last_seen_video_url = latest_video_url

        if state.pending_video_count > 0:
            state.sync_status = SyncStatus.RUNNING.value
            state.last_sync_at = now
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.failure_count = 0
            state.last_error = None
            state.version += 1
            _append_state_event(
                session,
                state=state,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger,
                event_type=SyncEventType.PHASE_CHANGED,
                event_phase=SyncPhase.EXTRACTING,
                event_status=SyncRunStatus.RUNNING,
                payload={
                    "cursor_payload": state.cursor_payload,
                    "latest_video_url": state.last_seen_video_url,
                    "source_video_count": source_video_count,
                    "videos_found": videos_found,
                    "videos_enqueued": videos_enqueued,
                    "pending_video_count": state.pending_video_count,
                    "feed_completed": True,
                },
                occurred_at=now,
            )
            return state

        _complete_sync_success_in_session(
            session,
            state=state,
            source_video_count=source_video_count,
            videos_found=videos_found,
            videos_enqueued=videos_enqueued,
            next_sync_at=next_sync_at,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
        )
        return state


def mark_sync_skipped(
    sync_state_id: int,
    *,
    next_sync_at: datetime | None = None,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
    reason: str | None = None,
    event_type: str = SyncEventType.DEFERRED,
    event_phase: str = SyncPhase.DEFERRED,
    event_status: str = SyncRunStatus.DEFERRED,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.last_sync_at = now
        state.last_error = None
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.failure_count = 0
        state.next_sync_at = next_sync_at or (now + get_mode_interval(state.sync_mode))
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=event_type,
            event_phase=event_phase,
            event_status=event_status,
            payload={
                "reason": reason,
                "next_sync_at": state.next_sync_at,
                "pending_video_count": state.pending_video_count,
            },
            message=reason,
            occurred_at=now,
        )
        return state


def mark_sync_failed(
    sync_state_id: int,
    error_message: str,
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    error_type: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        started_at = state.locked_at
        state.failure_count += 1
        state.sync_status = SyncStatus.FAILED.value
        state.last_sync_at = now
        state.last_error = error_message
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.FAILED,
            event_phase=SyncPhase.FAILED,
            event_status=SyncRunStatus.FAILED,
            payload={
                "error_type": error_type or "sync_failed",
                "error_message": error_message,
                "failure_count": state.failure_count,
                "pending_video_count": state.pending_video_count,
                "next_sync_at": state.next_sync_at,
                "duration_ms": int((now - started_at).total_seconds() * 1000) if started_at else 0,
            },
            message=error_message,
            occurred_at=now,
        )
        return state


def defer_sync_state(
    sync_state_id: int,
    *,
    delay: timedelta,
    error_message: str | None = None,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        state.sync_status = SyncStatus.SUCCESS.value
        state.last_sync_at = now
        state.last_error = error_message
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + delay
        state.version += 1
        _append_state_event(
            session,
            state=state,
            run_id=run_id,
            request_id=request_id,
            trace_id=trace_id,
            trigger=trigger,
            event_type=SyncEventType.DEFERRED,
            event_phase=SyncPhase.DEFERRED,
            event_status=SyncRunStatus.DEFERRED,
            payload={
                "error_message": error_message,
                "pending_video_count": state.pending_video_count,
                "next_sync_at": state.next_sync_at,
            },
            message=error_message,
            occurred_at=now,
        )
        return state


def decrement_pending_video_count(
    sync_state_id: int | None,
    count: int = 1,
    *,
    run_id: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
    allow_completion: bool = True,
) -> None:
    if not sync_state_id or count <= 0:
        return
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return
        state.pending_video_count = max(0, state.pending_video_count - count)
        state.version += 1
        if (
            allow_completion
            and state.pending_video_count == 0
            and state.sync_status == SyncStatus.RUNNING.value
            and state.locked_at is None
            and _can_complete_drained_state(state.id)
        ):
            _complete_sync_success_in_session(
                session,
                state=state,
                run_id=run_id,
                request_id=request_id,
                trace_id=trace_id,
                trigger=trigger,
            )


def has_incremental_backpressure(sync_state: SubscriptionSyncState) -> bool:
    return sync_state.sync_mode == SyncMode.INCREMENTAL.value and sync_state.pending_video_count >= INCREMENTAL_PENDING_THRESHOLD
