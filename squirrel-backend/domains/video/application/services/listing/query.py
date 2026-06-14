from typing import Any

from sqlalchemy import false, func, literal, select

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
    def __init__(
        self,
        resolve_effective_nsfw_filter=None,
    ):
        resolve_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._build_active_subscriptions_query = (
            lambda **kwargs: build_active_subscriptions_query(
                **kwargs,
                resolve_effective_nsfw_filter_func=resolve_nsfw_filter,
            )
        )

    def build_list_query(
        self,
        *,
        user_id: int,
        show_nsfw: bool,
        subscription_id: int | None,
        query: str | None,
        category: str | None,
        sort_by: str,
        nsfw: str,
        domains: list[str] | None,
        time_range: str,
        duration: str,
        content_type: str,
        special: str,
        recalled_ids: list[int],
    ) -> Any:
        """Meili 召回后的 video_id 集合 + PG 权限/category 过滤 + 排序分页。

        - recalled_ids 由 service 层通过 Meili.recall() 获得（已含 domain/time/duration 下沉过滤 + 排序召回）
        - 召回为空 → 返回空结果集
        - 权限（订阅/nsfw/special）走 active_subscriptions join
        - category（read/unread/liked/later/preview）走 feed_category_predicate EXISTS（依赖 VideoHistory/Interaction）
        - content_type 走 active_subscriptions.c.subscription_type（用户订阅维度）
        - 排序：沿用 Meili 召回顺序（按 search_rank 优先，同 rank 内 PG 再排一遍保证稳定分页）
        """
        active_subscriptions = self._build_active_subscriptions_query(
            user_id=user_id,
            subscription_id=subscription_id,
            nsfw=nsfw,
            show_nsfw=show_nsfw,
            special=special,
        )

        # 召回为空（搜索词无匹配，或 Meili 未配置）→ 返回空结果集
        if not recalled_ids:
            return (
                select(
                    literal(0).label("video_id"),
                    literal(None).label("publish_date"),
                    literal(None).label("video_created_at"),
                    literal(0).label("search_rank"),
                    literal(None).label("sort_value"),
                )
                .where(false())
            )

        query_stmt = (
            select(
                Video.id.label("video_id"),
                Video.publish_date.label("publish_date"),
                Video.created_at.label("video_created_at"),
                literal(0).label("search_rank"),
            )
            .select_from(Video)
            .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
            .join(active_subscriptions, active_subscriptions.c.subscription_id == SubscriptionVideo.subscription_id)
            .where(
                Video.is_deleted.is_(False),
                Video.id.in_(recalled_ids),
            )
        )

        if content_type != "all":
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

        feed_source = query_stmt.subquery("feed_source")
        if sort_by == "created_at":
            sort_value = func.max(feed_source.c.video_created_at).label("sort_value")
        else:
            sort_value = func.max(feed_source.c.publish_date).label("sort_value")
        search_rank = func.max(feed_source.c.search_rank).label("search_rank")

        return (
            select(
                feed_source.c.video_id,
                func.max(feed_source.c.publish_date).label("publish_date"),
                func.max(feed_source.c.video_created_at).label("video_created_at"),
                search_rank,
                sort_value,
            )
            .group_by(feed_source.c.video_id)
            .order_by(search_rank.desc(), sort_value.desc(), feed_source.c.video_id.desc())
        )


video_list_query_service = VideoListQueryService()

build_list_query = video_list_query_service.build_list_query
