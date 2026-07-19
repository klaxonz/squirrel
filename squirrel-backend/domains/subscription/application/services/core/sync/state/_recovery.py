from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select

from domains.subscription.application.services.core.sync.run_service import mark_run_status_in_session
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import subscription_sync_task_types
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_run import SyncRunStatus
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncStatus

from ._completion import _complete_sync_success_in_session, _video_task_summary
from ._intervals import QUEUED_RECOVERY_GRACE, RUNNING_TIMEOUT, build_retry_delay
from ._stale import _has_live_subscription_task, _recover_stale_running_state
from .session import get_session


def recover_stale_sync_state(sync_state_id: int) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.execute(
            select(SubscriptionSyncState)
            .where(SubscriptionSyncState.id == sync_state_id)
            .with_for_update(),
        ).scalar_one_or_none()
        if not state:
            return None
        if state.sync_status != SyncStatus.RUNNING.value or not state.locked_at:
            return state
        if state.locked_at > now - RUNNING_TIMEOUT:
            return state
        if not _has_live_subscription_task(session, state, now):
            _recover_stale_running_state(state, now, session=session)
        return state


def reconcile_pending_video_counts() -> dict[str, int]:
    with get_session() as session:
        states = session.execute(
            select(SubscriptionSyncState)
            .where(
                or_(
                    SubscriptionSyncState.current_run_id.is_not(None),
                    SubscriptionSyncState.pending_video_count != 0,
                ),
            )
            .with_for_update(),
        ).scalars().all()
        counts = _scan_pending_video_counts(session)
        for state in states:
            pending_count = counts.get(state.id, 0)
            if state.pending_video_count != pending_count:
                state.pending_video_count = pending_count
                state.version += 1
    return {
        'states': len(counts),
        'videos': sum(counts.values()),
    }


def reconcile_terminal_drained_sync_states(sync_state_id: int | None = None) -> dict[str, int]:
    now = datetime.now()
    completed = 0
    failed = 0

    with get_session() as session:
        filters = (
            SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
            SubscriptionSyncState.locked_at.is_(None),
        )
        if sync_state_id is not None:
            filters = (*filters, SubscriptionSyncState.id == sync_state_id)

        states = session.execute(
            select(SubscriptionSyncState).where(*filters).with_for_update(skip_locked=True),
        ).scalars().all()

        for state in states:
            active_count, failed_count, last_error = _video_task_summary(
                session,
                state.id,
                state.current_run_id,
            )

            if active_count > 0:
                continue

            state.pending_video_count = 0

            if failed_count > 0:
                state.failure_count += 1
                state.sync_status = SyncStatus.FAILED.value
                state.last_sync_at = now
                run_id = state.current_run_id
                state.last_error = str(last_error or 'video_extract_failed')
                state.queue_token = None
                state.current_run_id = None
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
                    error_type='video_extract_failed',
                    now=now,
                )
                failed += 1
                continue

            _complete_sync_success_in_session(session, state=state)
            completed += 1

    return {
        'running_states': len(states),
        'completed': completed,
        'failed': failed,
    }


def recover_stale_queued_sync_states(grace: timedelta = QUEUED_RECOVERY_GRACE) -> dict[str, int]:
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        queued_states = (
            session.execute(
                select(SubscriptionSyncState).where(
                    SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                    SubscriptionSyncState.queued_at.is_not(None),
                    SubscriptionSyncState.queued_at <= now - grace,
                ).with_for_update(skip_locked=True),
            )
            .scalars()
            .all()
        )
        active_sync_state_ids = _scan_subscription_update_state_ids(session)

        for state in queued_states:
            if state.id in active_sync_state_ids:
                continue
            state.sync_status = SyncStatus.FAILED.value
            state.last_sync_at = now
            state.last_error = 'stale_queued_missing_message'
            run_id = state.current_run_id
            state.queue_token = None
            state.current_run_id = None
            state.queued_at = None
            state.locked_at = None
            state.next_sync_at = now
            state.version += 1
            mark_run_status_in_session(
                session,
                run_id,
                SyncRunStatus.FAILED.value,
                error_message=state.last_error,
                error_type='stale_queued_missing_task',
                now=now,
            )
            recovered += 1

    return {
        'queued_states': len(queued_states),
        'recovered': recovered,
    }


def recover_stale_running_sync_states(timeout: timedelta = RUNNING_TIMEOUT) -> dict[str, int]:
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        stale_before = now - timeout
        states = (
            session.execute(
                select(SubscriptionSyncState).where(
                    SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
                    SubscriptionSyncState.locked_at.is_not(None),
                    SubscriptionSyncState.locked_at <= stale_before,
                ).with_for_update(skip_locked=True),
            )
            .scalars()
            .all()
        )

        for state in states:
            if _has_live_subscription_task(session, state, now):
                continue
            _recover_stale_running_state(state, now, session=session)
            recovered += 1

    return {
        'running_states': len(states),
        'recovered': recovered,
    }


def recover_stale_sync_states_on_startup() -> dict[str, int]:
    """Recover all stale sync-state rows left by a crashed/interrupted process.

    Called once at scheduler-worker startup to reconcile drained terminal states,
    revive queued states whose message never arrived, and time out runs whose lease
    expired. Returns a flat summary dict; callers log only when something was recovered.
    """
    drained = reconcile_terminal_drained_sync_states()
    queued = recover_stale_queued_sync_states()
    running = recover_stale_running_sync_states()
    return {
        'drained_completed': int(drained.get('completed', 0)),
        'drained_failed': int(drained.get('failed', 0)),
        'queued_recovered': int(queued.get('recovered', 0)),
        'running_recovered': int(running.get('recovered', 0)),
    }


def _scan_pending_video_counts(session) -> dict[int, int]:
    rows = session.execute(
        select(CrawlTask.sync_state_id, func.count(CrawlTask.id))
        .join(SubscriptionSyncState, SubscriptionSyncState.id == CrawlTask.sync_state_id)
        .where(
            CrawlTask.task_type == 'video_extract',
            or_(
                CrawlTask.run_id == SubscriptionSyncState.current_run_id,
                and_(CrawlTask.run_id.is_(None), SubscriptionSyncState.current_run_id.is_(None)),
            ),
            CrawlTask.status.in_(
                [
                    CrawlTaskStatus.PENDING.value,
                    CrawlTaskStatus.LEASED.value,
                    CrawlTaskStatus.RUNNING.value,
                    CrawlTaskStatus.RETRY_WAIT.value,
                ],
            ),
        )
        .group_by(CrawlTask.sync_state_id),
    ).all()
    return {int(state_id): int(count) for state_id, count in rows if state_id is not None}


def _scan_subscription_update_state_ids(session) -> set[int]:
    state_ids = session.execute(
        select(CrawlTask.sync_state_id)
        .join(SubscriptionSyncState, SubscriptionSyncState.id == CrawlTask.sync_state_id)
        .where(
            CrawlTask.task_type.in_(subscription_sync_task_types()),
            or_(
                CrawlTask.run_id == SubscriptionSyncState.current_run_id,
                and_(CrawlTask.run_id.is_(None), SubscriptionSyncState.current_run_id.is_(None)),
            ),
            CrawlTask.status.in_(
                [
                    CrawlTaskStatus.PENDING.value,
                    CrawlTaskStatus.LEASED.value,
                    CrawlTaskStatus.RUNNING.value,
                    CrawlTaskStatus.RETRY_WAIT.value,
                ],
            ),
        )
        .distinct(),
    ).scalars()
    return {int(state_id) for state_id in state_ids if state_id is not None}
