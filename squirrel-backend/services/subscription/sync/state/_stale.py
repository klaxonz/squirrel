from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from models.subscription_sync_state import SubscriptionSyncState, SyncStatus
from services.crawl.tasks import service as crawl_task_service

from ._intervals import RUNNING_TIMEOUT


def _recover_stale_running_states_in_session(session: Session, now: datetime) -> None:
    stale_before = now - RUNNING_TIMEOUT
    states = session.execute(
        select(SubscriptionSyncState).where(
            SubscriptionSyncState.sync_status == SyncStatus.RUNNING.value,
            SubscriptionSyncState.locked_at.is_not(None),
            SubscriptionSyncState.locked_at <= stale_before,
        ),
    ).scalars().all()
    for state in states:
        _recover_stale_running_state(state, now)


def _recover_stale_running_state(state: SubscriptionSyncState, now: datetime) -> None:
    state.sync_status = SyncStatus.FAILED.value
    state.last_error = "stale_running_timeout"
    state.queue_token = None
    state.queued_at = None
    state.locked_at = None
    state.failure_count += 1
    state.next_sync_at = now
    state.version += 1


def _can_complete_drained_state(sync_state_id: int) -> bool:
    try:
        summary = crawl_task_service.summarize_video_task_states_by_sync_state()
    except SQLAlchemyError:
        return True

    stats = summary.get(sync_state_id, {})
    active_count = int(stats.get("active_count", 0) or 0)
    failed_count = int(stats.get("failed_count", 0) or 0)
    return failed_count == 0 and active_count <= 1
