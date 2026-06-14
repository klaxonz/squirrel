from typing import Any

from sqlalchemy import false, func, literal, select
from sqlalchemy.orm import Session

from domains.user.domain.models.user_video_feed import UserVideoFeed
from domains.video.application.services.listing.query_filters import (
    build_active_subscriptions_query,
    feed_category_predicate,
    normalize_domains,
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

    def build_feed_rows_query(
        self,
        *,
        user_id: int,
        show_nsfw: bool,
        subscription_id: int | None,
        category: str | None,
        sort_by: str,
        nsfw: str,
        domains: list[str] | None,
        special: str,
    ) -> Any:
        """浏览快路径：纯 PG 投影表查询，不调 Meili。

        domain 过滤在此保留 PG 侧（浏览路径不走 Meili 召回，故不下沉）。
        投影表读取将在 commit 5 改为实时 join，本方法届时同步迁移。
        """
        active_subscriptions = self._build_active_subscriptions_query(
            user_id=user_id,
            subscription_id=subscription_id,
            nsfw=nsfw,
            show_nsfw=show_nsfw,
            special=special,
        )
        query_stmt = (
            select(
                UserVideoFeed.video_id.label("video_id"),
                UserVideoFeed.publish_date.label("publish_date"),
                UserVideoFeed.video_created_at.label("video_created_at"),
            )
            .select_from(UserVideoFeed)
            .join(active_subscriptions, UserVideoFeed.subscription_id == active_subscriptions.c.subscription_id)
            .join(Video, Video.id == UserVideoFeed.video_id)
            .where(
                UserVideoFeed.user_id == user_id,
                Video.is_deleted.is_(False),
            )
        )

        if category:
            query_stmt = query_stmt.where(
                feed_category_predicate(
                    user_id,
                    category,
                    video_id_column=UserVideoFeed.video_id,
                    publish_date_column=UserVideoFeed.publish_date,
                )
            )

        normalized_domains = normalize_domains(domains)
        if normalized_domains:
            query_stmt = query_stmt.where(UserVideoFeed.domain.in_(normalized_domains))

        if sort_by == "created_at":
            return query_stmt.order_by(UserVideoFeed.video_created_at.desc(), UserVideoFeed.video_id.desc())
        return query_stmt.order_by(UserVideoFeed.publish_date.desc(), UserVideoFeed.video_id.desc())

    @staticmethod
    def fetch_feed_page_video_ids(session: Session, feed_rows_query: Any, *, offset: int, page_size: int) -> list[int]:
        """投影表/实时 join 的 fan-out 去重分页（同一 video 多个订阅会多行）。

        滚动窗口读取 + 集合去重，跳过 offset 前的已见 video_id。
        """
        video_ids: list[int] = []
        seen_video_ids: set[int] = set()
        row_offset = 0
        batch_size = max(page_size * 4, 100)

        while len(video_ids) < page_size:
            rows = session.execute(feed_rows_query.limit(batch_size).offset(row_offset)).all()
            if not rows:
                break

            row_offset += len(rows)
            for row in rows:
                if row.video_id in seen_video_ids:
                    continue
                seen_video_ids.add(row.video_id)
                if len(seen_video_ids) <= offset:
                    continue
                video_ids.append(row.video_id)
                if len(video_ids) >= page_size:
                    break

        return video_ids

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
        recalled_ids: list[int] | None,
    ) -> Any:
        """搜索/过滤路径：Meili 召回后的 video_id 集合 + PG 权限/category 过滤 + 排序分页。

        - recalled_ids 由 service 层通过 Meili.recall() 获得（已含 domain/time/duration 下沉过滤），
          故此处不再重复做这些过滤。
        - 权限（订阅/nsfw/special）走 active_subscriptions join。
        - category（read/unread/liked/later/preview）走 feed_category_predicate EXISTS（依赖 VideoHistory/Interaction）。
        - content_type 走 active_subscriptions.c.subscription_type（用户订阅维度，非全局）。
        """
        active_subscriptions = self._build_active_subscriptions_query(
            user_id=user_id,
            subscription_id=subscription_id,
            nsfw=nsfw,
            show_nsfw=show_nsfw,
            special=special,
        )

        # 召回为空（搜索词无匹配，或仅结构化过滤但 Meili 未配置）→ 返回空结果集
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

build_feed_rows_query = video_list_query_service.build_feed_rows_query
build_list_query = video_list_query_service.build_list_query
fetch_feed_page_video_ids = video_list_query_service.fetch_feed_page_video_ids
