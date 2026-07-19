from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.application.services.core.sync.run_service import mark_run_status_in_session
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import subscription_sync_task_types
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_run import SyncRunStatus
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState, SyncStatus

from ._intervals import RUNNING_TIMEOUT


def _recover_stale_running_states_in_session(session: Session, now: datetime) -> None:
    stale_before = now - RUNNING_TIMEOUT
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


def _recover_stale_running_state(
    state: SubscriptionSyncState,
    now: datetime,
    *,
    session: Session | None = None,
) -> None:
    run_id = state.current_run_id
    state.sync_status = SyncStatus.FAILED.value
    state.last_error = 'stale_running_timeout'
    state.queue_token = None
    state.current_run_id = None
    state.execution_token = None
    state.queued_at = None
    state.locked_at = None
    state.failure_count += 1
    state.next_sync_at = now
    state.version += 1
    if session is not None:
        mark_run_status_in_session(
            session,
            run_id,
            SyncRunStatus.FAILED.value,
            error_message=state.last_error,
            error_type='stale_running_timeout',
            now=now,
        )


def _has_live_subscription_task(session: Session, state: SubscriptionSyncState, now: datetime) -> bool:
    if not state.current_run_id:
        return False
    tasks = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.run_id == state.current_run_id,
            CrawlTask.sync_state_id == state.id,
            CrawlTask.task_type.in_(subscription_sync_task_types()),
            CrawlTask.status.in_(
                [
                    CrawlTaskStatus.PENDING.value,
                    CrawlTaskStatus.RETRY_WAIT.value,
                    CrawlTaskStatus.LEASED.value,
                    CrawlTaskStatus.RUNNING.value,
                ],
            ),
        )
        .with_for_update(),
    ).scalars().all()
    return any(
        task.status in {CrawlTaskStatus.PENDING.value, CrawlTaskStatus.RETRY_WAIT.value}
        or (
            task.status in {CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value}
            and task.lease_until is not None
            and task.lease_until >= now
        )
        for task in tasks
    )
