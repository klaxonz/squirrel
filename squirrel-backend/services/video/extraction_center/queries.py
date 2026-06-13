from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from models.links import UserSubscription
from models.subscription import Subscription
from models.video_extraction_projection import VideoExtractionProjection
from services.search.query import escape_ilike
from services.site_catalog.catalog import SiteCatalog


def base_projection_query(
    user_id: int,
    *,
    site_candidates: set[str] | None = None,
    normalized_query: str = '',
) -> Any:
    query = (
        select(VideoExtractionProjection, Subscription)
        .join(Subscription, Subscription.id == VideoExtractionProjection.subscription_id)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
    )
    if site_candidates:
        query = query.where(VideoExtractionProjection.site.in_(site_candidates))
    if normalized_query:
        query = query.where(Subscription.name.ilike(f'%{escape_ilike(normalized_query)}%'))
    return query


def apply_status_filter(query: Any, status: str | None) -> Any:
    normalized_status = (status or '').strip().lower() or None
    if normalized_status == 'running':
        return query.where(VideoExtractionProjection.display_status == 'running')
    if normalized_status == 'queued':
        return query.where(VideoExtractionProjection.display_status == 'queued')
    if normalized_status == 'failed':
        return query.where(VideoExtractionProjection.sync_status == 'failed')
    if normalized_status == 'recent':
        return query.where(VideoExtractionProjection.display_status.notin_(['running', 'queued']))
    return query


def apply_ordering(query: Any, status: str | None) -> Any:
    normalized_status = (status or '').strip().lower() or None
    if normalized_status == 'running':
        return query.order_by(
            VideoExtractionProjection.locked_at.asc(),
            VideoExtractionProjection.subscription_id.asc(),
        )
    if normalized_status == 'queued':
        return query.order_by(
            VideoExtractionProjection.queued_at.asc(),
            VideoExtractionProjection.subscription_id.asc(),
        )
    recent_dt = func.coalesce(VideoExtractionProjection.updated_at, VideoExtractionProjection.last_success_at)
    return query.order_by(recent_dt.desc(), VideoExtractionProjection.subscription_id.desc())


def resolve_site_candidates(site: str | None) -> set[str]:
    normalized_site = (site or '').strip().lower() or None
    return set(SiteCatalog.expand_site_filter_values(normalized_site)) if normalized_site else set()


def overview_query(user_id: int) -> Any:
    return (
        select(
            func.coalesce(
                func.sum(case((VideoExtractionProjection.display_status == 'running', 1), else_=0)),
                0,
            ).label('running_count'),
            func.coalesce(
                func.sum(case((VideoExtractionProjection.display_status == 'queued', 1), else_=0)),
                0,
            ).label('queued_count'),
            func.coalesce(
                func.sum(case((VideoExtractionProjection.sync_status == 'failed', 1), else_=0)),
                0,
            ).label('failed_count'),
            func.coalesce(func.sum(VideoExtractionProjection.pending_video_count), 0).label('pending_videos'),
            func.coalesce(func.sum(VideoExtractionProjection.queued_task_count), 0).label('queue_depth'),
        )
        .select_from(VideoExtractionProjection)
        .join(Subscription, Subscription.id == VideoExtractionProjection.subscription_id)
        .join(UserSubscription, UserSubscription.subscription_id == Subscription.id)
        .where(
            UserSubscription.user_id == user_id,
            UserSubscription.is_deleted.is_(False),
            Subscription.is_deleted.is_(False),
        )
    )


def list_projection_rows(
    session: Session,
    *,
    user_id: int,
    status: str | None,
    site: str | None,
    query: str | None,
    page: int,
    page_size: int,
) -> tuple[list[tuple[VideoExtractionProjection, Subscription]], int]:
    normalized_status = (status or '').strip().lower() or None
    filtered_query = apply_status_filter(
        base_projection_query(
            user_id,
            site_candidates=resolve_site_candidates(site),
            normalized_query=(query or '').strip().lower(),
        ),
        normalized_status,
    )
    ordered_query = apply_ordering(filtered_query, normalized_status)
    start = max(0, (page - 1) * page_size)

    total = int(
        session.execute(
            select(func.count()).select_from(filtered_query.order_by(None).subquery()),
        ).scalar()
        or 0,
    )
    rows = session.execute(
        ordered_query.offset(start).limit(page_size),
    ).all()
    return rows, total
