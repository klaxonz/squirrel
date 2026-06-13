from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select, update

from models.crawl_task import CrawlTask
from models.subscription_sync_run_projection import SubscriptionSyncRunProjection
from models.subscription_sync_state import SubscriptionSyncState, SyncStatus
from models.subscription_sync_subscription_projection import SubscriptionSyncSubscriptionProjection
from services.crawl.tasks import service as crawl_task_service
from services.crawl.tasks.task_types import subscription_sync_task_types
from services.subscription.sync.run_service import SyncEventType, SyncPhase, SyncRunStatus

from ._completion import _complete_sync_success_in_session
from ._events import _append_recovery_run_events, _append_terminal_reconcile_run_events
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
        _append_recovery_run_events(
            session,
            state=state,
            event_type=SyncEventType.STALE_RUNNING_RECOVERED,
            event_phase=SyncPhase.FAILED,
            event_status=SyncRunStatus.TIMEOUT,
            reason="stale_running_timeout",
            occurred_at=now,
        )
        return state


def reconcile_retry_wait_run_projections() -> dict[str, int]:
    scanned = 0
    repaired = 0
    now = datetime.now()
    feed_phase_candidates = {
        SyncPhase.FETCHING_FEED,
        SyncPhase.CALCULATING_DELTA,
        SyncPhase.ENQUEUEING,
    }

    with get_session() as session:
        rows = session.execute(
            select(
                SubscriptionSyncSubscriptionProjection,
                SubscriptionSyncRunProjection,
                SubscriptionSyncState,
            )
            .join(
                SubscriptionSyncRunProjection,
                SubscriptionSyncRunProjection.run_id == SubscriptionSyncSubscriptionProjection.latest_run_id,
            )
            .join(
                SubscriptionSyncState,
                SubscriptionSyncState.id == SubscriptionSyncRunProjection.sync_state_id,
            )
            .where(
                SubscriptionSyncSubscriptionProjection.current_status == SyncRunStatus.RUNNING,
                SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                SubscriptionSyncRunProjection.current_phase.in_(feed_phase_candidates),
            ),
        ).all()

        subscription_ids = {
            state.subscription_id
            for _, _, state in rows
            if state.subscription_id is not None
        }
        if not subscription_ids:
            return {
                "candidates": 0,
                "repaired": 0,
            }

        tasks = session.execute(
            select(CrawlTask)
            .where(
                CrawlTask.task_type.in_(subscription_sync_task_types()),
                CrawlTask.status == "retry_wait",
                CrawlTask.last_error == "lease_expired",
                CrawlTask.subscription_id.in_(subscription_ids),
            )
            .order_by(CrawlTask.id.desc()),
        ).scalars().all()

        latest_task_by_sync_state: dict[int, CrawlTask] = {}
        for task in tasks:
            sync_state_id = (task.payload or {}).get("sync_state_id")
            try:
                sync_state_id = int(sync_state_id)
            except (TypeError, ValueError):
                continue
            latest_task_by_sync_state.setdefault(sync_state_id, task)

        for _, run_projection, state in rows:
            scanned += 1
            task = latest_task_by_sync_state.get(state.id)
            if not task:
                continue

            task_payload = task.payload or {}
            task_run_id = str(task_payload.get("run_id") or "").strip() or None
            if task_run_id and task_run_id != run_projection.run_id:
                continue
            error_message = str(task.last_error or state.last_error or "").strip()
            occurred_at = state.queued_at or task.updated_at or now
            from ._events import _append_state_event
            _append_state_event(
                session,
                state=state,
                run_id=run_projection.run_id,
                request_id=run_projection.request_id,
                trace_id=run_projection.trace_id,
                trigger=run_projection.trigger,
                event_type=SyncEventType.QUEUED,
                event_phase=SyncPhase.QUEUED,
                event_status=SyncRunStatus.QUEUED,
                payload={
                    "queue_token": state.queue_token or task_payload.get("queue_token"),
                    "queued_at": occurred_at,
                    "pending_video_count": state.pending_video_count,
                    "error_message": error_message,
                },
                message=error_message,
                occurred_at=occurred_at,
            )
            repaired += 1

    return {
        "candidates": scanned,
        "repaired": repaired,
    }


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
        "states": len(counts),
        "videos": sum(counts.values()),
    }


def reconcile_terminal_drained_sync_states() -> dict[str, int]:
    summary = crawl_task_service.summarize_video_task_states_by_sync_state()
    now = datetime.now()
    completed = 0
    failed = 0

    with get_session() as session:
        states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
                SubscriptionSyncState.locked_at.is_(None),
            ),
        ).scalars().all()

        for state in states:
            stats = summary.get(state.id, {})
            active_count = int(stats.get("active_count", 0) or 0)
            failed_count = int(stats.get("failed_count", 0) or 0)

            if active_count > 0:
                continue

            state.pending_video_count = 0

            if failed_count > 0:
                state.failure_count += 1
                state.sync_status = SyncStatus.FAILED.value
                state.last_sync_at = now
                state.last_error = str(stats.get("last_error") or "video_extract_failed")
                state.queue_token = None
                state.queued_at = None
                state.locked_at = None
                state.idle_sync_count = 0
                state.next_sync_at = now + build_retry_delay(state.sync_mode, state.failure_count)
                state.version += 1
                _append_terminal_reconcile_run_events(
                    session,
                    state=state,
                    event_type=SyncEventType.FAILED,
                    event_phase=SyncPhase.FAILED,
                    event_status=SyncRunStatus.FAILED,
                    reason="video_extract_reconcile_failed",
                    error_message=state.last_error,
                    occurred_at=now,
                )
                failed += 1
                continue

            _complete_sync_success_in_session(session, state=state)
            _append_terminal_reconcile_run_events(
                session,
                state=state,
                event_type=SyncEventType.COMPLETED,
                event_phase=SyncPhase.COMPLETED,
                event_status=SyncRunStatus.SUCCESS,
                reason="video_extract_reconcile_completed",
                error_message=None,
                occurred_at=now,
            )
            completed += 1

    return {
        "running_states": len(states),
        "completed": completed,
        "failed": failed,
    }


def recover_stale_queued_sync_states(grace: timedelta = QUEUED_RECOVERY_GRACE) -> dict[str, int]:
    active_sync_state_ids = _scan_subscription_update_state_ids()
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        queued_states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.sync_status == SyncStatus.QUEUED.value,
                SubscriptionSyncState.queued_at.is_not(None),
                SubscriptionSyncState.queued_at <= now - grace,
            ),
        ).scalars().all()

        for state in queued_states:
            if state.id in active_sync_state_ids:
                continue
            state.sync_status = SyncStatus.FAILED.value
            state.last_sync_at = now
            state.last_error = "stale_queued_missing_message"
            state.queue_token = None
            state.queued_at = None
            state.locked_at = None
            state.next_sync_at = now
            state.version += 1
            _append_recovery_run_events(
                session,
                state=state,
                event_type=SyncEventType.STALE_QUEUED_RECOVERED,
                event_phase=SyncPhase.FAILED,
                event_status=SyncRunStatus.FAILED,
                reason="stale_queued_missing_message",
                occurred_at=now,
            )
            recovered += 1

    return {
        "queued_states": len(queued_states),
        "recovered": recovered,
    }


def recover_stale_running_sync_states(timeout: timedelta = RUNNING_TIMEOUT) -> dict[str, int]:
    now = datetime.now()
    recovered = 0

    with get_session() as session:
        stale_before = now - timeout
        states = session.execute(
            select(SubscriptionSyncState).where(
                SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
                SubscriptionSyncState.locked_at.is_not(None),
                SubscriptionSyncState.locked_at <= stale_before,
            ),
        ).scalars().all()

        for state in states:
            _recover_stale_running_state(state, now)
            _append_recovery_run_events(
                session,
                state=state,
                event_type=SyncEventType.STALE_RUNNING_RECOVERED,
                event_phase=SyncPhase.FAILED,
                event_status=SyncRunStatus.TIMEOUT,
                reason="stale_running_timeout",
                occurred_at=now,
            )
            recovered += 1

    return {
        "running_states": len(states),
        "recovered": recovered,
    }


def _scan_pending_video_counts() -> dict[int, int]:
    return crawl_task_service.count_pending_video_tasks_by_sync_state()


def _scan_subscription_update_state_ids() -> set[int]:
    return crawl_task_service.list_active_subscription_sync_state_ids()

