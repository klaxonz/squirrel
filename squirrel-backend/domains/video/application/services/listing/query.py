from typing import Any

from sqlalchemy import false, func, literal, select
from sqlalchemy.orm import Session

from domains.user.domain.models.user_video_feed import UserVideoFeed
from domains.video.application.services.listing.query_filters import (
    build_active_subscriptions_query,
    contains_text,
    feed_category_predicate,
    feed_time_range_predicates,
    normalize_domains,
)
from domains.video.application.services.moderation.nsfw_policy import (
    resolve_effective_nsfw_filter as _default_resolve_effective_nsfw_filter,
)
from domains.video.application.services.search.query import duration_predicate as _default_duration_predicate
from domains.video.domain.models.video import Video


class VideoListQueryService:
    def __init__(
        self,
        resolve_effective_nsfw_filter=None,
        duration_predicate=None,
        parse_search_query=None,
        normalize_subscription_type_term=None,
    ):
        self._duration_predicate = duration_predicate or _default_duration_predicate
        resolve_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._build_active_subscriptions_query = (
            lambda **kwargs: build_active_subscriptions_query(
                **kwargs,
                resolve_effective_nsfw_filter_func=resolve_nsfw_filter,
            )
        )

        if parse_search_query is None:
            from infrastructure.search.query import parse_search_query as _psq
            self._parse_search_query = _psq
        else:
            self._parse_search_query = parse_search_query

        if normalize_subscription_type_term is None:
            from infrastructure.search.query import normalize_subscription_type_term as _nstt
            self._normalize_subscription_type_term = _nstt
        else:
            self._normalize_subscription_type_term = normalize_subscription_type_term

    @staticmethod
    def _title_search_conditions(parsed_query: Any, *, domain_column: Any = Video.domain) -> list[Any]:
        conditions: list[Any] = []

        for term in parsed_query.text_terms:
            conditions.append(contains_text(Video.title, term))

        for term in parsed_query.get("title"):
            conditions.append(contains_text(Video.title, term))

        for term in parsed_query.get("domain"):
            conditions.append(contains_text(domain_column, term))

        return conditions

    def _subscription_search_query(
        self,
        *,
        active_subscriptions: Any,
        parsed_query: Any,
        user_id: int,
        sort_by: str,
        domains: list[str] | None,
        category: str | None,
        time_range: str,
        duration: str,
    ):
        subscription_query = (
            select(
                UserVideoFeed.video_id.label("video_id"),
                UserVideoFeed.publish_date.label("publish_date"),
                UserVideoFeed.video_created_at.label("video_created_at"),
                literal(60).label("search_rank"),
            )
            .select_from(active_subscriptions)
            .join(UserVideoFeed, UserVideoFeed.subscription_id == active_subscriptions.c.subscription_id)
            .join(Video, Video.id == UserVideoFeed.video_id)
            .where(
                UserVideoFeed.user_id == user_id,
                Video.is_deleted.is_(False),
            )
        )

        subscription_terms = parsed_query.get("subscription")
        text_terms = parsed_query.text_terms if not parsed_query.get("title") else []
        for term in subscription_terms + text_terms:
            subscription_query = subscription_query.where(contains_text(active_subscriptions.c.subscription_name, term))

        for term in parsed_query.get("type"):
            normalized_type = self._normalize_subscription_type_term(term)
            if normalized_type:
                subscription_query = subscription_query.where(active_subscriptions.c.subscription_type == normalized_type)

        normalized_domains = normalize_domains(domains)
        if normalized_domains:
            subscription_query = subscription_query.where(UserVideoFeed.domain.in_(normalized_domains))

        if category:
            subscription_query = subscription_query.where(
                feed_category_predicate(
                    user_id,
                    category,
                    video_id_column=UserVideoFeed.video_id,
                    publish_date_column=UserVideoFeed.publish_date,
                )
            )

        for cond in feed_time_range_predicates(time_range):
            subscription_query = subscription_query.where(cond)
        for cond in self._duration_predicate(duration):
            subscription_query = subscription_query.where(cond)

        feed_source = subscription_query.subquery("subscription_search_source")
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
        recalled_ids: list[int] | None = None,
    ) -> Any:
        active_subscriptions = self._build_active_subscriptions_query(
            user_id=user_id,
            subscription_id=subscription_id,
            nsfw=nsfw,
            show_nsfw=show_nsfw,
            special=special,
        )
        parsed_query = self._parse_search_query(query)

        # Meilisearch 召回路径：recalled_ids 非空时用召回集合过滤，
        # 跳过 legacy 的字段解析（subscription/type/unsupported 早期分支 + title 搜索条件），
        # 因为召回已覆盖 title/description/subscription/creator 全文匹配。
        if recalled_ids is None:
            has_unsupported_terms = any(
                [
                    parsed_query.get("creator"),
                    parsed_query.get("url"),
                    parsed_query.get("description"),
                ]
            )

            if parsed_query.get("subscription") or parsed_query.get("type"):
                return self._subscription_search_query(
                    active_subscriptions=active_subscriptions,
                    parsed_query=parsed_query,
                    user_id=user_id,
                    sort_by=sort_by,
                    domains=domains,
                    category=category,
                    time_range=time_range,
                    duration=duration,
                )

            if has_unsupported_terms:
                return (
                    select(
                        Video.id.label("video_id"),
                        Video.publish_date.label("publish_date"),
                        Video.created_at.label("video_created_at"),
                        literal(0).label("search_rank"),
                        Video.publish_date.label("sort_value"),
                    )
                    .select_from(Video)
                    .where(false())
                )
        elif not recalled_ids:
            # 搜索词无任何匹配 → 返回空，避免 IN () 退化为全表
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
                UserVideoFeed.video_id.label("video_id"),
                UserVideoFeed.publish_date.label("publish_date"),
                UserVideoFeed.video_created_at.label("video_created_at"),
                literal(0).label("search_rank"),
            )
            .select_from(UserVideoFeed)
            .join(active_subscriptions, UserVideoFeed.subscription_id == active_subscriptions.c.subscription_id)
            .join(Video, Video.id == UserVideoFeed.video_id)
            .where(
                UserVideoFeed.user_id == user_id,
                Video.is_deleted.is_(False),
            )
        )

        if content_type != "all":
            query_stmt = query_stmt.where(active_subscriptions.c.subscription_type == content_type)

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

        for cond in feed_time_range_predicates(time_range):
            query_stmt = query_stmt.where(cond)
        for cond in self._duration_predicate(duration):
            query_stmt = query_stmt.where(cond)

        if recalled_ids is not None:
            query_stmt = query_stmt.where(UserVideoFeed.video_id.in_(recalled_ids))
        else:
            search_conditions = self._title_search_conditions(parsed_query, domain_column=UserVideoFeed.domain)
            for cond in search_conditions:
                query_stmt = query_stmt.where(cond)

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
