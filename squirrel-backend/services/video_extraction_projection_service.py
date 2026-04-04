from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from threading import Lock
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.crawl_task import CrawlTask
from models.video_extraction_projection import VideoExtractionProjection


RUNNING_TASK_STATUSES = {'leased', 'running'}
QUEUED_TASK_STATUSES = {'pending', 'retry_wait'}
FAILED_TASK_STATUSES = {'dead', 'cancelled'}
COMPLETED_TASK_STATUSES = {'succeeded'}
VIDEO_EXTRACT_TASK_TYPE = 'video_extract'

_seed_lock = Lock()


def _sync_state_value_expr():
    return func.nullif(CrawlTask.payload['sync_state_id'].as_string(), '')


def _derive_group_key(task: CrawlTask) -> tuple[str, str]:
    payload = task.payload or {}
    sync_state_id = payload.get('sync_state_id')
    if sync_state_id not in (None, ''):
        return 'state', str(sync_state_id)
    return 'job', str(task.job_id)


def _compute_projection_snapshot(tasks: list[CrawlTask]) -> dict[str, object]:
    total_count = len(tasks)
    queued_count = sum(1 for task in tasks if task.status in QUEUED_TASK_STATUSES)
    running_count = sum(1 for task in tasks if task.status in RUNNING_TASK_STATUSES)
    completed_count = sum(1 for task in tasks if task.status in COMPLETED_TASK_STATUSES)
    failed_count = sum(1 for task in tasks if task.status in FAILED_TASK_STATUSES)
    active_count = queued_count + running_count

    if running_count > 0:
        sync_status = 'running'
        display_status = 'running'
        current_phase = 'extracting'
    elif active_count > 0:
        sync_status = 'queued'
        display_status = 'queued'
        current_phase = 'queued'
    elif failed_count > 0:
        sync_status = 'failed'
        display_status = 'failed'
        current_phase = 'completed'
    else:
        sync_status = 'success'
        display_status = 'healthy'
        current_phase = 'completed'

    latest_failed_task = max(
        (task for task in tasks if task.status in FAILED_TASK_STATUSES),
        key=lambda item: (item.updated_at or datetime.min, item.id),
        default=None,
    )

    queued_at = min((task.created_at for task in tasks if task.created_at), default=None)
    locked_at = min((task.started_at for task in tasks if task.started_at), default=None)
    updated_at = max((task.updated_at for task in tasks if task.updated_at), default=None)
    last_success_at = max(
        (task.finished_at for task in tasks if task.status in COMPLETED_TASK_STATUSES and task.finished_at),
        default=None,
    )
    first_task = tasks[0] if tasks else None

    return {
        'site': first_task.site if first_task else None,
        'sync_status': sync_status,
        'display_status': display_status,
        'current_phase': current_phase,
        'last_error': latest_failed_task.last_error if latest_failed_task else None,
        'queued_at': queued_at,
        'locked_at': locked_at,
        'last_success_at': last_success_at if sync_status == 'success' else None,
        'pending_video_count': active_count,
        'batch_task_count': total_count,
        'queued_task_count': queued_count,
        'running_task_count': running_count,
        'completed_task_count': completed_count,
        'failed_task_count': failed_count,
        'updated_at': updated_at or datetime.now(),
    }


def _upsert_projection(
    session: Session,
    *,
    subscription_id: int,
    group_kind: str,
    group_value: str,
    snapshot: dict[str, object],
) -> None:
    projection = session.execute(
        select(VideoExtractionProjection).where(
            VideoExtractionProjection.subscription_id == subscription_id,
            VideoExtractionProjection.group_kind == group_kind,
            VideoExtractionProjection.group_value == group_value,
        )
    ).scalar_one_or_none()

    if projection is None:
        projection = VideoExtractionProjection(
            subscription_id=subscription_id,
            group_kind=group_kind,
            group_value=group_value,
        )
        session.add(projection)

    for key, value in snapshot.items():
        setattr(projection, key, value)


def refresh_projection_for_task(task: CrawlTask, *, session: Optional[Session] = None) -> None:
    if task.task_type != VIDEO_EXTRACT_TASK_TYPE or task.subscription_id is None:
        return

    group_kind, group_value = _derive_group_key(task)
    if session is not None:
        _refresh_projection_group(session, subscription_id=int(task.subscription_id), group_kind=group_kind, group_value=group_value)
        return

    with get_session() as managed_session:
        _refresh_projection_group(
            managed_session,
            subscription_id=int(task.subscription_id),
            group_kind=group_kind,
            group_value=group_value,
        )


def _refresh_projection_group(
    session: Session,
    *,
    subscription_id: int,
    group_kind: str,
    group_value: str,
) -> None:
    subscription_tasks = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE,
            CrawlTask.subscription_id == subscription_id,
        )
        .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc())
    ).scalars().all()
    tasks = [
        task for task in subscription_tasks
        if _derive_group_key(task) == (group_kind, str(group_value))
    ]

    projection = session.execute(
        select(VideoExtractionProjection).where(
            VideoExtractionProjection.subscription_id == subscription_id,
            VideoExtractionProjection.group_kind == group_kind,
            VideoExtractionProjection.group_value == group_value,
        )
    ).scalar_one_or_none()

    if not tasks:
        if projection is not None:
            session.delete(projection)
        return

    snapshot = _compute_projection_snapshot(tasks)
    _upsert_projection(
        session,
        subscription_id=subscription_id,
        group_kind=group_kind,
        group_value=group_value,
        snapshot=snapshot,
    )


def rebuild_all_projections(*, session: Optional[Session] = None) -> int:
    if session is not None:
        return _rebuild_all(session)

    with get_session() as managed_session:
        return _rebuild_all(managed_session)


def _rebuild_all(session: Session) -> int:
    tasks = session.execute(
        select(CrawlTask)
        .where(CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE)
        .order_by(CrawlTask.subscription_id.asc(), CrawlTask.job_id.asc(), CrawlTask.created_at.asc(), CrawlTask.id.asc())
    ).scalars().all()

    session.execute(VideoExtractionProjection.__table__.delete())
    grouped: dict[tuple[int, str, str], list[CrawlTask]] = defaultdict(list)
    for task in tasks:
        if task.subscription_id is None:
            continue
        group_kind, group_value = _derive_group_key(task)
        grouped[(int(task.subscription_id), group_kind, group_value)].append(task)

    for (subscription_id, group_kind, group_value), group_tasks in grouped.items():
        _upsert_projection(
            session,
            subscription_id=subscription_id,
            group_kind=group_kind,
            group_value=group_value,
            snapshot=_compute_projection_snapshot(group_tasks),
        )

    session.flush()
    return len(grouped)


def ensure_projection_seeded() -> int:
    with _seed_lock:
        with get_session() as session:
            projection_count = int(session.execute(select(func.count(VideoExtractionProjection.id))).scalar() or 0)
            if projection_count > 0:
                return 0

            task_count = int(
                session.execute(
                    select(func.count(CrawlTask.id)).where(CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE)
                ).scalar()
                or 0
            )
            if task_count == 0:
                return 0

            return _rebuild_all(session)
