from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update

from domains.subscription.application.services.core.sync.run_service import SyncEventType, SyncPhase, SyncRunStatus
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus

from ._crud import _get_or_create_sync_state_in_session
from ._events import _append_state_event
from ._intervals import INCREMENTAL_PENDING_THRESHOLD, build_retry_delay, get_mode_interval
from ._stale import _recover_stale_running_state
from .session import get_session


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


def has_incremental_backpressure(sync_state: SubscriptionSyncState) -> bool:
    return sync_state.sync_mode == SyncMode.INCREMENTAL.value and sync_state.pending_video_count >= INCREMENTAL_PENDING_THRESHOLD
