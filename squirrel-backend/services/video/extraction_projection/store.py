from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models.crawl_task import CrawlTask
from models.video_extraction_projection import VideoExtractionProjection
from services.video.extraction_projection.groups import (
    ACTIVE_PROJECTION_STATUSES,
    QUEUED_TASK_STATUSES,
    RUNNING_TASK_STATUSES,
    VIDEO_EXTRACT_TASK_TYPE,
    derive_group_key,
)
from services.video.extraction_projection.snapshot import compute_projection_snapshot


def refresh_projection_group(
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
        .order_by(CrawlTask.created_at.asc(), CrawlTask.id.asc()),
    ).scalars().all()
    tasks = [
        task for task in subscription_tasks
        if derive_group_key(task) == (group_kind, str(group_value))
    ]

    projection = session.execute(
        select(VideoExtractionProjection).where(
            VideoExtractionProjection.subscription_id == subscription_id,
            VideoExtractionProjection.group_kind == group_kind,
            VideoExtractionProjection.group_value == group_value,
        ),
    ).scalar_one_or_none()

    if not tasks:
        if projection is not None:
            session.delete(projection)
        return

    upsert_projection(
        session,
        subscription_id=subscription_id,
        group_kind=group_kind,
        group_value=group_value,
        snapshot=compute_projection_snapshot(tasks),
    )


def rebuild_all(session: Session) -> int:
    tasks = session.execute(
        select(CrawlTask)
        .where(CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE)
        .order_by(CrawlTask.subscription_id.asc(), CrawlTask.job_id.asc(), CrawlTask.created_at.asc(), CrawlTask.id.asc()),
    ).scalars().all()

    session.execute(VideoExtractionProjection.__table__.delete())
    grouped: dict[tuple[int, str, str], list[CrawlTask]] = defaultdict(list)
    for task in tasks:
        if task.subscription_id is None:
            continue
        group_kind, group_value = derive_group_key(task)
        grouped[(int(task.subscription_id), group_kind, group_value)].append(task)

    for (subscription_id, group_kind, group_value), group_tasks in grouped.items():
        upsert_projection(
            session,
            subscription_id=subscription_id,
            group_kind=group_kind,
            group_value=group_value,
            snapshot=compute_projection_snapshot(group_tasks),
        )

    session.flush()
    return len(grouped)


def reconcile_active_projection_drift(session: Session) -> int:
    stale_keys = load_active_task_group_keys(session) | load_active_projection_group_keys(session)

    refreshed = 0
    for subscription_id, group_kind, group_value in stale_keys:
        refresh_projection_group(
            session,
            subscription_id=subscription_id,
            group_kind=group_kind,
            group_value=group_value,
        )
        refreshed += 1

    session.flush()
    return refreshed


def projection_requires_group_key_rebuild(session: Session) -> bool:
    state_rows = session.execute(
        select(
            VideoExtractionProjection.subscription_id,
            VideoExtractionProjection.group_value,
        ).where(VideoExtractionProjection.group_kind == 'state'),
    ).all()
    if not state_rows:
        return False

    state_keys = {
        (int(subscription_id), str(group_value))
        for subscription_id, group_value in state_rows
    }
    tasks = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE,
            CrawlTask.subscription_id.is_not(None),
        )
        .limit(1000),
    ).scalars().all()

    for task in tasks:
        if task.subscription_id is None:
            continue
        payload = task.payload or {}
        run_id = payload.get('run_id')
        sync_state_id = payload.get('sync_state_id')
        if run_id in (None, '') or sync_state_id in (None, ''):
            continue
        if (int(task.subscription_id), str(sync_state_id)) in state_keys:
            return True

    return False


def count_projections(session: Session) -> int:
    return int(session.execute(select(func.count(VideoExtractionProjection.id))).scalar() or 0)


def count_video_extract_tasks(session: Session) -> int:
    return int(
        session.execute(
            select(func.count(CrawlTask.id)).where(CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE),
        ).scalar()
        or 0,
    )


def upsert_projection(
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
        ),
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


def load_active_task_group_keys(session: Session) -> set[tuple[int, str, str]]:
    tasks = session.execute(
        select(CrawlTask)
        .where(
            CrawlTask.task_type == VIDEO_EXTRACT_TASK_TYPE,
            CrawlTask.status.in_(RUNNING_TASK_STATUSES | QUEUED_TASK_STATUSES),
            CrawlTask.subscription_id.is_not(None),
        ),
    ).scalars().all()

    keys: set[tuple[int, str, str]] = set()
    for task in tasks:
        if task.subscription_id is None:
            continue
        group_kind, group_value = derive_group_key(task)
        keys.add((int(task.subscription_id), group_kind, group_value))
    return keys


def load_active_projection_group_keys(session: Session) -> set[tuple[int, str, str]]:
    rows = session.execute(
        select(
            VideoExtractionProjection.subscription_id,
            VideoExtractionProjection.group_kind,
            VideoExtractionProjection.group_value,
        ).where(VideoExtractionProjection.display_status.in_(ACTIVE_PROJECTION_STATUSES)),
    ).all()
    return {
        (int(subscription_id), str(group_kind), str(group_value))
        for subscription_id, group_kind, group_value in rows
    }
