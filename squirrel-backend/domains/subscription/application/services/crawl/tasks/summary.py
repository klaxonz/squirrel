from datetime import datetime

from sqlalchemy import func, select

from domains.subscription.application.services.crawl.tasks.models import CrawlTaskStatus
from domains.subscription.application.services.crawl.tasks.task_types import subscription_sync_task_types
from domains.subscription.domain.models.crawl_task import CrawlTask

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
        tasks = (
            session.execute(
                select(CrawlTask).where(
                    CrawlTask.task_type == 'video_extract',
                    CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                ),
            )
            .scalars()
            .all()
        )
    counts: dict[int, int] = {}
    for task in tasks:
        sync_state_id = (task.payload or {}).get('sync_state_id')
        if sync_state_id in (None, ''):
            continue
        counts[int(sync_state_id)] = counts.get(int(sync_state_id), 0) + 1
    return counts


def summarize_video_task_states_by_sync_state(session_factory) -> dict[int, dict[str, object]]:
    with session_factory() as session:
        tasks = (
            session.execute(
                select(CrawlTask).where(CrawlTask.task_type == 'video_extract'),
            )
            .scalars()
            .all()
        )

    summary: dict[int, dict[str, object]] = {}
    for task in tasks:
        sync_state_id = (task.payload or {}).get('sync_state_id')
        if sync_state_id in (None, ''):
            continue

        key = int(sync_state_id)
        bucket = summary.setdefault(
            key,
            {
                'active_count': 0,
                'failed_count': 0,
                'last_error': None,
                'last_error_at': datetime.min,
            },
        )

        if task.status in ACTIVE_TASK_STATUSES:
            bucket['active_count'] = int(bucket['active_count']) + 1
            continue

        if task.status not in FAILED_TASK_STATUSES:
            continue

        bucket['failed_count'] = int(bucket['failed_count']) + 1
        error_at = task.updated_at or task.finished_at or task.created_at or datetime.min
        if error_at >= bucket['last_error_at']:
            bucket['last_error_at'] = error_at
            bucket['last_error'] = task.last_error or task.last_error_type or 'video_extract_failed'

    for bucket in summary.values():
        bucket.pop('last_error_at', None)

    return summary


def list_active_subscription_sync_state_ids(session_factory) -> set[int]:
    with session_factory() as session:
        tasks = (
            session.execute(
                select(CrawlTask).where(
                    CrawlTask.task_type.in_(subscription_sync_task_types()),
                    CrawlTask.status.in_(ACTIVE_TASK_STATUSES),
                ),
            )
            .scalars()
            .all()
        )
    state_ids: set[int] = set()
    for task in tasks:
        sync_state_id = (task.payload or {}).get('sync_state_id')
        if sync_state_id in (None, ''):
            continue
        state_ids.add(int(sync_state_id))
    return state_ids
