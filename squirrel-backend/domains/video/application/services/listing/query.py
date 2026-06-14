
from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.video.application.services.listing.query_filters import (
    build_active_subscriptions_query,
    feed_category_predicate,
)
from domains.video.application.services.moderation.nsfw_policy import (
    resolve_effective_nsfw_filter as _default_resolve_effective_nsfw_filter,
)
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video


class VideoListQueryService:
    def __init__(self, resolve_effective_nsfw_filter=None):
        resolve_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._build_active_subscriptions_query = (
            lambda **kwargs: build_active_subscriptions_query(
                **kwargs,
                resolve_effective_nsfw_filter_func=resolve_nsfw_filter,
            )
        )

    def filter_recalled_ids(
        self,
        session: Session,
        *,
        recalled_ids: list[int],
        user_id: int,
        show_nsfw: bool,
        subscription_id: int | None,
        category: str,
        nsfw: str,
        content_type: str,
        special: str,
    ) -> list[int]:
        """对 Meili 召回的 video_id 集合做 PG 权限 + category 过滤，保持召回顺序返回。

        PG 负责：
        - 权限（订阅/nsfw/special）走 active_subscriptions join
        - category（read/unread/liked/later/preview）走 feed_category_predicate EXISTS
        - content_type 走 active_subscriptions.c.subscription_type
        返回值按 recalled_ids 原始顺序去重（Meili 的排序即最终顺序）。
        """
        if not recalled_ids:
            return []

        active_subscriptions = self._build_active_subscriptions_query(
            user_id=user_id,
            subscription_id=subscription_id,
            nsfw=nsfw,
            show_nsfw=show_nsfw,
            special=special,
        )

        query_stmt = (
            select(Video.id)
            .select_from(Video)
            .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(active_subscriptions, active_subscriptions.c.subscription_id == SubscriptionVideo.subscription_id)
            .where(
                Video.is_deleted.is_(False),
                Video.id.in_(recalled_ids),
            )
        )

        if content_type != 'all':
            query_stmt = query_stmt.where(active_subscriptions.c.subscription_type == content_type)

        if category:
            query_stmt = query_stmt.where(
                feed_category_predicate(
                    user_id,
                    category,
                    video_id_column=Video.id,
                    publish_date_column=Video.publish_date,
                )
            )

        # fan-out 去重（同一 video 多个订阅会多行），取 set
        matched = {row[0] for row in session.execute(query_stmt).all()}

        # 按召回顺序返回（Meili 的排序即最终展示顺序）
        return [vid for vid in recalled_ids if vid in matched]


video_list_query_service = VideoListQueryService()

# 模块级便捷函数
filter_recalled_ids = video_list_query_service.filter_recalled_ids


def recall_offset_ids(
    *,
    query: str,
    domains: list[str] | None,
    time_range: str,
    duration: str,
    limit: int = 5000,
) -> list[int]:
    """搜索场景 Meili 召回（OFFSET 分页用）。失败抛出由调用方处理。"""
    from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
    return get_meili_video_indexer().recall(
        query,
        domains=domains,
        time_range=time_range,
        duration=duration,
        limit=limit,
    )
