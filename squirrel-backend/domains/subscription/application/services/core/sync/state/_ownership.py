from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.subscription.application.services.crawl.tasks.clock import database_local_now_expression
from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import is_subscription_sync_task_type
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState


def has_live_execution_token(
    session: Session,
    state: SubscriptionSyncState,
    execution_token: str | None,
    *,
    require_state_match: bool = True,
) -> bool:
    """Validate the execution fence against the authoritative task lease."""
    if not execution_token:
        return False
    if require_state_match and state.execution_token != execution_token:
        return False
    if execution_token.startswith('direct:'):
        return bool(state.current_run_id) and execution_token == f'direct:{state.current_run_id}'

    task = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.sync_state_id == state.id,
            CrawlTask.run_id == state.current_run_id,
            CrawlTask.lease_token == execution_token,
            CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]),
            CrawlTask.lease_until.is_not(None),
            CrawlTask.lease_until >= database_local_now_expression(session),
        )
        .with_for_update(),
    ).scalar_one_or_none()
    return task is not None and is_subscription_sync_task_type(task.task_type)


def has_live_video_task_token(
    session: Session,
    state: SubscriptionSyncState,
    *,
    run_id: str | None,
    execution_token: str | None,
    task_id: int | None,
) -> bool:
    """Validate a video child's lease independently from its completed parent."""
    if not run_id or state.current_run_id != run_id or not execution_token or not task_id:
        return False
    task = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.id == task_id,
            CrawlTask.task_type == 'video_extract',
            CrawlTask.sync_state_id == state.id,
            CrawlTask.run_id == run_id,
            CrawlTask.lease_token == execution_token,
            CrawlTask.status.in_([CrawlTaskStatus.LEASED.value, CrawlTaskStatus.RUNNING.value]),
            CrawlTask.lease_until.is_not(None),
            CrawlTask.lease_until >= database_local_now_expression(session),
        )
        .with_for_update(),
    ).scalar_one_or_none()
    return task is not None
