from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.sync.run_service import mark_run_status_in_session
from domains.subscription.domain.models.subscription_sync_run import SyncRunStatus
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncMode, SyncStatus

from ._crud import _get_or_create_sync_state_in_session
from ._intervals import INCREMENTAL_PENDING_THRESHOLD, RUNNING_TIMEOUT, build_retry_delay, get_mode_interval
from ._ownership import has_live_execution_token
from ._stale import _has_live_subscription_task, _recover_stale_running_state
from .session import get_session


def deactivate_sync_states(subscription_id: int, *, reason: str = 'deactivated') -> int:
    with get_session() as session:
        return deactivate_sync_states_in_session(session, subscription_id, reason=reason)


def deactivate_sync_states_in_session(
    session: Session,
    subscription_id: int,
    *,
    reason: str = 'deactivated',
    states: list[SubscriptionSyncState] | None = None,
    now: datetime | None = None,
) -> int:
    current_time = now or datetime.now()
    updated_count = 0
    if states is None:
        states = (
            session.execute(
                select(SubscriptionSyncState)
                .where(SubscriptionSyncState.subscription_id == subscription_id)
                .order_by(SubscriptionSyncState.id.asc())
                .with_for_update(),
            )
            .scalars()
            .all()
        )

    for state in states:
        mark_run_status_in_session(
            session,
            state.current_run_id,
            SyncRunStatus.CANCELLED.value,
            error_message=reason,
            now=current_time,
        )
        state.sync_status = SyncStatus.IDLE.value
        state.last_error = reason
        state.queue_token = None
        state.current_run_id = None
        state.execution_token = None
        state.queued_at = None
        state.locked_at = None
        state.pending_video_count = 0
        state.last_sync_at = current_time
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
        return prepare_sync_state_for_enqueue_in_session(
            session,
            subscription_id,
            url,
            mode,
            scheduled=scheduled,
            now=now,
        )


def prepare_sync_state_for_enqueue_in_session(
    session: Session,
    subscription_id: int,
    url: str | None,
    mode: str,
    *,
    scheduled: bool,
    now: datetime | None = None,
) -> tuple[SubscriptionSyncState | None, str]:
    current_time = now or datetime.now()
    state = _get_or_create_sync_state_in_session(session, subscription_id, mode, url)
    if (
        state.sync_status == SyncStatus.RUNNING.value
        and state.locked_at is not None
        and state.locked_at <= current_time - RUNNING_TIMEOUT
        and not _has_live_subscription_task(session, state, current_time)
    ):
        _recover_stale_running_state(state, current_time, session=session)

    if state.sync_status == SyncStatus.RUNNING.value:
        return state, 'in_progress'
    if state.sync_status == SyncStatus.QUEUED.value:
        return state, 'queued'

    if scheduled and has_incremental_backpressure(state):
        state.sync_status = SyncStatus.SUCCESS.value
        state.last_sync_at = current_time
        state.last_error = 'queue_backpressure'
        state.queue_token = None
        state.queued_at = None
        state.locked_at = None
        state.next_sync_at = current_time + get_mode_interval(state.sync_mode)
        state.version += 1
        return state, 'deferred'

    return state, 'ready'


def queue_sync_state(sync_state_id: int, queue_token: str, run_id: str) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        return queue_sync_state_in_session(
            session,
            sync_state_id,
            queue_token,
            run_id,
            now=now,
        )


def queue_sync_state_in_session(
    session: Session,
    sync_state_id: int,
    queue_token: str,
    run_id: str,
    *,
    now: datetime | None = None,
) -> SubscriptionSyncState | None:
    current_time = now or datetime.now()
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
            current_run_id=run_id,
            execution_token=None,
            queued_at=current_time,
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
    execution_token: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.execute(
            select(SubscriptionSyncState)
            .where(SubscriptionSyncState.id == sync_state_id)
            .with_for_update(),
        ).scalar_one_or_none()
        if (
            state is None
            or state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}
            or state.queue_token != queue_token
            or state.current_run_id != run_id
            or not has_live_execution_token(
                session,
                state,
                execution_token,
                require_state_match=False,
            )
        ):
            return None
        state.sync_status = SyncStatus.RUNNING.value
        state.execution_token = execution_token
        state.locked_at = now
        state.last_sync_at = now
        state.version += 1
        mark_run_status_in_session(
            session,
            run_id,
            SyncRunStatus.RUNNING.value,
            queue_token=queue_token,
            now=now,
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
    execution_token: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    trigger: str | None = None,
) -> SubscriptionSyncState | None:
    if not sync_state_id:
        return None

    now = now or datetime.now()
    expected_token = str(queue_token or '').strip() or None

    with get_session() as session:
        state = session.execute(
            select(SubscriptionSyncState)
            .where(SubscriptionSyncState.id == sync_state_id)
            .with_for_update(),
        ).scalar_one_or_none()
        if not state:
            return None

        current_token = str(state.queue_token or '').strip() or None
        if run_id and state.current_run_id != run_id:
            return state
        if state.execution_token != execution_token:
            return state
        if expected_token and current_token != expected_token:
            return state

        if retryable:
            if state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
                return state
            state.sync_status = SyncStatus.QUEUED.value
            state.queue_token = expected_token or state.queue_token
            state.execution_token = None
            state.queued_at = now
            state.locked_at = None
            state.last_error = error_message
            state.version += 1
            mark_run_status_in_session(
                session,
                run_id,
                SyncRunStatus.QUEUED.value,
                queue_token=state.queue_token,
                error_message=error_message,
                now=now,
            )
            return state

        if state.sync_status not in {SyncStatus.QUEUED.value, SyncStatus.RUNNING.value}:
            return state

        state.failure_count += 1
        state.sync_status = SyncStatus.FAILED.value
        state.last_sync_at = now
        state.last_error = error_message or 'task_retry_exhausted'
        state.queue_token = None
        state.current_run_id = None
        state.execution_token = None
        state.queued_at = None
        state.locked_at = None
        state.idle_sync_count = 0
        state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
        state.version += 1
        mark_run_status_in_session(
            session,
            run_id,
            SyncRunStatus.FAILED.value,
            error_message=state.last_error,
            error_type='task_retry_exhausted',
            now=now,
        )
        return state


def has_incremental_backpressure(sync_state: SubscriptionSyncState) -> bool:
    return (
        sync_state.sync_mode == SyncMode.INCREMENTAL.value
        and sync_state.pending_video_count >= INCREMENTAL_PENDING_THRESHOLD
    )
