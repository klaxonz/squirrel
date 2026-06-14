from typing import Any

from sqlalchemy import and_, exists, false, func, select
from sqlalchemy.orm import Session

import infrastructure.site_catalog.url as url_helper
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from domains.video.domain.models.video_history import VideoHistory
from infrastructure.config.settings import settings
from infrastructure.site_catalog.catalog import SiteCatalog


def _recall_video_ids_for_history(query: str | None) -> list[int]:
    """有搜索词时用 Meili 召回 video_id；无搜索词返回空（history 走全量）。"""
    if not query or not query.strip() or not settings.MEILISEARCH_URL:
        return []
    try:
        return get_meili_video_indexer().recall(query)
    except Exception:
        # 召回失败：history 搜索降级为无搜索词（返回空集合会被 IN 过滤成空结果，
        # 故这里返回空列表仅在 query 非空时意味着"搜不到"，符合失败语义）
        return []


def build_history_conditions(user_id: int, filters: dict, effective_nsfw: str) -> list[Any] | None:
    conditions = [
        VideoHistory.user_id == user_id,
        exists(
            select(1).select_from(Video).where(Video.id == VideoHistory.video_id),
        ),
    ]

    # 搜索词：Meili 召回匹配的 video_id 集合，加 IN 过滤
    if filters.get('query'):
        recalled = _recall_video_ids_for_history(filters['query'])
        if not recalled:
            # 召回空 = 无匹配，强制返回空结果
            conditions.append(false())
        else:
            conditions.append(VideoHistory.video_id.in_(recalled))

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
        # nsfw 过滤改用实时 join（UserSubscription.is_nsfw），不再依赖 user_video_feed
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
                UserSubscription.is_deleted.is_(False),
                UserSubscription.is_nsfw,
            ),
        )
        if effective_nsfw == 'yes':
            conditions.append(nsfw_history_exists)
        elif effective_nsfw == 'no':
            conditions.append(~nsfw_history_exists)
    if filters.get('site'):
        # 统一走 SiteCatalog.resolve_domains（修复预先存在的不一致：history 原先用原始 site 字符串）
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
