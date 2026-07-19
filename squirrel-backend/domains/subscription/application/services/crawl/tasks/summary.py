from datetime import datetime

from sqlalchemy import and_, case, func, or_, select

from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import subscription_sync_task_types
from domains.subscription.domain.models.crawl_task import CrawlTask
from domains.subscription.domain.models.subscription_sync_state import SubscriptionSyncState

ACTIVE_TASK_STATUSES = [
    CrawlTaskStatus.PENDING.value,
    CrawlTaskStatus.LEASED.value,
    CrawlTaskStatus.RUNNING.value,
    CrawlTaskStatus.RETRY_WAIT.value,
]
FAILED_TASK_STATUSES = [
    CrawlTaskStatus.DEAD.value,
    CrawlTaskStatus.CANCELLED.value,
]


def _current_run_filter():
    return or_(
        CrawlTask.run_id == SubscriptionSyncState.current_run_id,
        and_(CrawlTask.run_id.is_(None), SubscriptionSyncState.current_run_id.is_(None)),
    )


def count_pending_video_tasks_for_subscription(session_factory, subscription_id: int) -> int:
    with session_factory() as session:
        value = session.execute(
            select(func.count(CrawlTask.id)).where(
                CrawlTask.task_type == 'video_extract',
                CrawlTask.subscription_id == subscription_id,
                CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
            ),
        ).scalar_one()
    return int(value or 0)


def count_pending_video_tasks_by_sync_state(session_factory) -> dict[int, int]:
    with session_factory() as session:
        rows = session.execute(
            select(CrawlTask.sync_state_id, func.count(CrawlTask.id))
            .join(SubscriptionSyncState, SubscriptionSyncState.id == CrawlTask.sync_state_id)
            .where(
                CrawlTask.task_type == 'video_extract',
                CrawlTask.sync_state_id.is_not(None),
                CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                _current_run_filter(),
            )
            .group_by(CrawlTask.sync_state_id),
        ).all()
    return {int(sync_state_id): int(count) for sync_state_id, count in rows if sync_state_id is not None}


def summarize_video_task_states_by_sync_state(
    session_factory,
    sync_state_id: int | None = None,
) -> dict[int, dict[str, object]]:
    filters = [
        CrawlTask.task_type == 'video_extract',
        CrawlTask.sync_state_id.is_not(None),
        _current_run_filter(),
    ]
    if sync_state_id is not None:
        filters.append(CrawlTask.sync_state_id == sync_state_id)

    with session_factory() as session:
        rows = session.execute(
            select(
                CrawlTask.sync_state_id,
                func.sum(case((CrawlTask.status.in_(ACTIVE_TASK_STATUSES), 1), else_=0)),
                func.sum(case((CrawlTask.status.in_(FAILED_TASK_STATUSES), 1), else_=0)),
            )
            .join(SubscriptionSyncState, SubscriptionSyncState.id == CrawlTask.sync_state_id)
            .where(*filters)
            .group_by(CrawlTask.sync_state_id),
        ).all()

        summary: dict[int, dict[str, object]] = {}
        for row_sync_state_id, active_count, failed_count in rows:
            if row_sync_state_id is None:
                continue
            summary[int(row_sync_state_id)] = {
                'active_count': int(active_count or 0),
                'failed_count': int(failed_count or 0),
                'last_error': None,
            }

        if summary:
            failed_error_time = func.coalesce(CrawlTask.updated_at, CrawlTask.finished_at, CrawlTask.created_at, datetime.min)
            ranked_errors = (
                select(
                    CrawlTask.sync_state_id.label('sync_state_id'),
                    func.coalesce(CrawlTask.last_error, CrawlTask.last_error_type, 'video_extract_failed').label('last_error'),
                    func.row_number()
                    .over(
                        partition_by=CrawlTask.sync_state_id,
                        order_by=(failed_error_time.desc(), CrawlTask.id.desc()),
                    )
                    .label('error_rank'),
                )
                .join(SubscriptionSyncState, SubscriptionSyncState.id == CrawlTask.sync_state_id)
                .where(
                    *filters,
                    CrawlTask.status.in_(FAILED_TASK_STATUSES),
                )
                .subquery()
            )
            error_rows = session.execute(
                select(ranked_errors.c.sync_state_id, ranked_errors.c.last_error).where(ranked_errors.c.error_rank == 1),
            ).all()
            for error_sync_state_id, last_error in error_rows:
                if error_sync_state_id is not None:
                    summary[int(error_sync_state_id)]['last_error'] = last_error

    return summary


def list_active_subscription_sync_state_ids(session_factory) -> set[int]:
    with session_factory() as session:
        state_ids = session.execute(
            select(CrawlTask.sync_state_id)
            .join(SubscriptionSyncState, SubscriptionSyncState.id == CrawlTask.sync_state_id)
            .where(
                CrawlTask.task_type.in_(subscription_sync_task_types()),
                CrawlTask.sync_state_id.is_not(None),
                CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                _current_run_filter(),
            )
            .distinct(),
        ).scalars().all()
    return {int(sync_state_id) for sync_state_id in state_ids if sync_state_id is not None}
