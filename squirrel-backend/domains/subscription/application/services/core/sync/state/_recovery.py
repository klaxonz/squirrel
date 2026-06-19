from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update

from domains.subscription.application.services.crawl.tasks import service as crawl_task_service
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncStatus

from ._completion import _complete_sync_success_in_session
from ._intervals import QUEUED_RECOVERY_GRACE, RUNNING_TIMEOUT, build_retry_delay
from ._stale import _recover_stale_running_state
from .session import get_session


def recover_stale_sync_state(sync_state_id: int) -> SubscriptionSyncState | None:
    now = datetime.now()
    with get_session() as session:
        state = session.get(SubscriptionSyncState, sync_state_id)
        if not state:
            return None
        if state.sync_status != SyncStatus.RUNNING.value or not state.locked_at:
            return state
        if state.locked_at > now - RUNNING_TIMEOUT:
            return state
        _recover_stale_running_state(state, now)
        return state


def reconcile_pending_video_counts() -> dict[str, int]:
    counts = _scan_pending_video_counts()
    with get_session() as session:
        session.execute(
            update(SubscriptionSyncState)
            .where(SubscriptionSyncState.pending_video_count != 0)
            .values(pending_video_count=0),
        )
        for sync_state_id, pending_count in counts.items():
            session.execute(
                update(SubscriptionSyncState)
                .where(SubscriptionSyncState.id == sync_state_id)
                .values(pending_video_count=pending_count),
            )
    return {
        'states': len(counts),
        'videos': sum(counts.values()),
    }


def reconcile_terminal_drained_sync_states() -> dict[str, int]:
    summary = crawl_task_service.summarize_video_task_states_by_sync_state()
    now = datetime.now()
    completed = 0
    failed = 0

    with get_session() as session:
        states = (
            session.execute(
                select(SubscriptionSyncState).where(
                    SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
                    SubscriptionSyncState.locked_at.is_(None),
                ),
            )
            .scalars()
            .all()
        )

        for state in states:
            stats = summary.get(state.id, {})
            active_count = int(stats.get('active_count', 0) or 0)
            failed_count = int(stats.get('failed_count', 0) or 0)

            if active_count > 0:
                continue

            state.pending_video_count = 0

            if failed_count > 0:
                state.failure_count += 1
                state.sync_status = SyncStatus.FAILED.value
                state.last_sync_at = now
                state.last_error = str(stats.get('last_error') or 'video_extract_failed')
                state.queue_token = None
                state.queued_at = None
                state.locked_at = None
                state.idle_sync_count = 0
                state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
                state.version += 1
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
    active_sync_state_ids = _scan_subscription_update_state_ids()
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        queued_states = (
            session.execute(
                select(SubscriptionSyncState).where(
                    SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                    SubscriptionSyncState.queued_at.is_not(None),
                    SubscriptionSyncState.queued_at <= now - grace,
                ),
            )
            .scalars()
            .all()
        )

        for state in queued_states:
            if state.id in active_sync_state_ids:
                continue
            state.sync_status = SyncStatus.FAILED.value
            state.last_sync_at = now
            state.last_error = 'stale_queued_missing_message'
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.next_sync_at = now
            state.version += 1
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
                ),
            )
            .scalars()
            .all()
        )

        for state in states:
            _recover_stale_running_state(state, now)
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


def _scan_pending_video_counts() -> dict[int, int]:
    return crawl_task_service.count_pending_video_tasks_by_sync_state()


def _scan_subscription_update_state_ids() -> set[int]:
    return crawl_task_service.list_active_subscription_sync_state_ids()
