from typing import Any

from sqlalchemy import and_, exists, false, func, select
from sqlalchemy.orm import Session

from models.links import SubscriptionVideo, UserSubscription
from models.video import Video
from models.video_history import VideoHistory
from services.site_catalog.catalog import SiteCatalog
from services.video.search.query import build_video_search_clauses
from utils import url_helper


def build_history_conditions(user_id: int, filters: dict, effective_nsfw: str) -> list[Any] | None:
    conditions = [
        VideoHistory.user_id == user_id,
        exists(
            select(1).select_from(Video).where(Video.id == VideoHistory.video_id),
        ),
    ]

    if filters.get('query'):
        search_clauses = build_video_search_clauses(
            user_id=user_id,
            query=filters['query'],
            video_id_column=VideoHistory.video_id,
        )
        if search_clauses:
            conditions.extend(search_clauses)

    if filters.get('video_id'):
        conditions.append(VideoHistory.video_id == filters['video_id'])
    if filters.get('min_duration'):
        conditions.append(VideoHistory.duration >= filters['min_duration'])
    if filters.get('start_date'):
        conditions.append(VideoHistory.end_time >= filters['start_date'])
    if filters.get('end_date'):
        conditions.append(VideoHistory.end_time <= filters['end_date'])
    if effective_nsfw == 'blocked':
        conditions.append(false())
    elif effective_nsfw != 'all':
        nsfw_history_exists = exists(
            select(1)
            .select_from(SubscriptionVideo)
            .join(
                UserSubscription,
                UserSubscription.subscription_id == SubscriptionVideo.subscription_id,
            )
            .where(
                SubscriptionVideo.video_id == VideoHistory.video_id,
                UserSubscription.user_id == user_id,
                UserSubscription.is_nsfw,
            ),
        )
        if effective_nsfw == 'yes':
            conditions.append(nsfw_history_exists)
        elif effective_nsfw == 'no':
            conditions.append(~nsfw_history_exists)
    if filters.get('site'):
        resolved_domains = SiteCatalog.resolve_domains(filters['site'])
        normalized_domains = [
            domain
            for domain in {url_helper.normalize_domain(raw_domain) for raw_domain in resolved_domains if raw_domain}
            if domain
        ]
        if not normalized_domains:
            return None
        conditions.append(
            exists(
                select(1)
                .select_from(Video)
                .where(
                    and_(
                        Video.id == VideoHistory.video_id,
                        Video.domain.in_(normalized_domains),
                    ),
                ),
            ),
        )

    return conditions


def list_history_page(
    session: Session,
    *,
    user_id: int,
    filters: dict,
    page: int,
    page_size: int,
    effective_nsfw: str,
) -> tuple[list[VideoHistory], int]:
    conditions = build_history_conditions(user_id, filters, effective_nsfw)
    if conditions is None:
        return [], 0

    ranked_histories = (
        select(
            VideoHistory.id.label('id'),
            VideoHistory.end_time.label('end_time'),
            func.row_number()
            .over(
                partition_by=VideoHistory.video_id,
                order_by=(VideoHistory.end_time.desc(), VideoHistory.id.desc()),
            )
            .label('row_num'),
        )
        .where(*conditions)
        .subquery()
    )

    latest_history_ids = (
        select(
            ranked_histories.c.id,
            ranked_histories.c.end_time,
        )
        .where(ranked_histories.c.row_num == 1)
        .subquery()
    )

    total = session.scalar(
        select(func.count()).select_from(latest_history_ids),
    )

    histories = session.scalars(
        select(VideoHistory)
        .join(latest_history_ids, latest_history_ids.c.id == VideoHistory.id)
        .order_by(latest_history_ids.c.end_time.desc(), VideoHistory.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size),
    ).all()
    return histories, total or 0
