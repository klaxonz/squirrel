from datetime import timedelta
from typing import Any

from sqlalchemy import and_, exists, false, func, select

from models.links import SubscriptionVideo, UserSubscription
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from services.search.query import normalize_subscription_type_term as _default_normalize_subscription_type_term
from services.search.query import parse_search_query as _default_parse_search_query
from services.video.moderation.nsfw_policy import (
    resolve_effective_nsfw_filter as _default_resolve_effective_nsfw_filter,
)
from services.video.search.search_query import VideoSearchQueryBuilder
from utils import url_helper


class VideoQueryService:
    def __init__(
        self,
        resolve_effective_nsfw_filter=None,
        parse_search_query=None,
        normalize_subscription_type_term=None,
    ):
        self._resolve_effective_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._search_query_builder = VideoSearchQueryBuilder(
            parse_search_query=parse_search_query or _default_parse_search_query,
            normalize_subscription_type_term=normalize_subscription_type_term or _default_normalize_subscription_type_term,
        )

    def build_video_search_clauses(self, *, user_id: int, query: str | None, video_id_column: Any, subscription_id_column: Any = None) -> list[Any]:
        return self._search_query_builder.build_clauses(
            user_id=user_id,
            query=query,
            video_id_column=video_id_column,
            subscription_id_column=subscription_id_column,
        )

    def _build_base_video_conditions(
            self,
            user_id: int,
            show_nsfw: bool,
            subscription_id: int | None = None,
            query: str | None = None,
            nsfw: str = "all",
            domains: list[str] | None = None,
            time_range: str = "all",
            duration: str = "all",
            content_type: str = "all",
    ) -> list[Any]:
        conditions = [
            not Video.is_deleted,
            not UserSubscription.is_deleted,
            not Subscription.is_deleted,
            UserSubscription.user_id == user_id,
        ]

        if subscription_id:
            conditions.append(SubscriptionVideo.subscription_id == subscription_id)

        effective_nsfw = self._resolve_effective_nsfw_filter(nsfw, show_nsfw)

        if effective_nsfw == "blocked":
            conditions.append(false())
        elif effective_nsfw == "yes":
            conditions.append(UserSubscription.is_nsfw)
        elif effective_nsfw == "no":
            conditions.append(not UserSubscription.is_nsfw)

        conditions.extend(self.build_video_search_clauses(
            user_id=user_id,
            query=query,
            video_id_column=Video.id,
        ))

        if domains:
            normalized_domains = [
                d for d in {url_helper.normalize_domain(domain) for domain in domains if domain} if d
            ]
            if normalized_domains:
                conditions.append(Video.domain.in_(normalized_domains))

        conditions.extend(self.time_range_predicate(time_range))
        conditions.extend(self.duration_predicate(duration))
        conditions.extend(self.content_type_predicate(content_type))

        return conditions

    def build_base_video_query(
            self,
            user_id: int,
            show_nsfw: bool,
            subscription_id: int | None = None,
            query: str | None = None,
            nsfw: str = "all",
            domains: list[str] | None = None,
            time_range: str = "all",
            duration: str = "all",
            content_type: str = "all",
    ) -> Any:
        """Build base video query with Video as the main table."""
        base_query = (
            select(Video, SubscriptionVideo.subscription_id.label("subscription_id"))
            .select_from(Video)
            .join(SubscriptionVideo, Video.id == SubscriptionVideo.video_id)
            .join(UserSubscription, SubscriptionVideo.subscription_id == UserSubscription.subscription_id)
            .join(Subscription, UserSubscription.subscription_id == Subscription.id)
        )

        return base_query.where(
            and_(*self._build_base_video_conditions(
                user_id, show_nsfw, subscription_id, query, nsfw, domains,
                time_range, duration, content_type,
            )),
        )

    def build_video_count_source_query(
            self,
            user_id: int,
            show_nsfw: bool,
            subscription_id: int | None = None,
            query: str | None = None,
            nsfw: str = "all",
            domains: list[str] | None = None,
            time_range: str = "all",
            duration: str = "all",
            content_type: str = "all",
    ) -> Any:
        user_subscriptions = (
            select(UserSubscription.subscription_id.label("subscription_id"))
            .select_from(UserSubscription)
            .join(Subscription, Subscription.id == UserSubscription.subscription_id)
            .where(
                and_(
                    not UserSubscription.is_deleted,
                    not Subscription.is_deleted,
                    UserSubscription.user_id == user_id,
                ),
            )
        )

        if subscription_id:
            user_subscriptions = user_subscriptions.where(UserSubscription.subscription_id == subscription_id)

        effective_nsfw = self._resolve_effective_nsfw_filter(nsfw, show_nsfw)

        if effective_nsfw == "blocked":
            user_subscriptions = user_subscriptions.where(false())
        elif effective_nsfw == "yes":
            user_subscriptions = user_subscriptions.where(UserSubscription.is_nsfw)
        elif effective_nsfw == "no":
            user_subscriptions = user_subscriptions.where(not UserSubscription.is_nsfw)

        user_subscriptions = user_subscriptions.cte("user_subscriptions")

        count_source = (
            select(
                Video.id.label("video_id"),
                Video.publish_date.label("publish_date"),
            )
            .select_from(user_subscriptions)
            .join(SubscriptionVideo, SubscriptionVideo.subscription_id == user_subscriptions.c.subscription_id)
            .join(Video, Video.id == SubscriptionVideo.video_id)
            .where(not Video.is_deleted)
        )

        search_clauses = self.build_video_search_clauses(
            user_id=user_id,
            query=query,
            video_id_column=Video.id,
        )
        if search_clauses:
            count_source = count_source.where(*search_clauses)

        if domains:
            normalized_domains = [
                d for d in {url_helper.normalize_domain(domain) for domain in domains if domain} if d
            ]
            if normalized_domains:
                count_source = count_source.where(Video.domain.in_(normalized_domains))

        time_conds = self.time_range_predicate(time_range)
        dur_conds = self.duration_predicate(duration)
        type_clause = self.content_type_predicate(content_type)

        if time_conds or dur_conds or type_clause:
            count_source = count_source.join(
                SubscriptionVideo,
                SubscriptionVideo.video_id == Video.id,
            ).join(
                Subscription,
                Subscription.id == SubscriptionVideo.subscription_id,
            )
            for cond in time_conds:
                count_source = count_source.where(cond)
            for cond in dur_conds:
                count_source = count_source.where(cond)
            for cond in type_clause:
                count_source = count_source.where(cond)

        return count_source.distinct()

    @staticmethod
    def category_predicate(user_id: int, category: str | None) -> Any:
        """Return category filter condition, reused in list/count/random."""
        published = Video.publish_date <= func.now()

        if category == "preview":
            return Video.publish_date > func.now()
        if category == "read":
            return and_(
                published,
                exists(
                    select(1).where(
                        and_(
                            VideoHistory.user_id == user_id,
                            VideoHistory.video_id == Video.id,
                        ),
                    ),
                ),
            )
        if category == "unread":
            return and_(
                published,
                ~exists(
                    select(1).where(
                        and_(
                            VideoHistory.user_id == user_id,
                            VideoHistory.video_id == Video.id,
                        ),
                    ),
                ),
            )
        if category == "liked":
            return and_(
                published,
                exists(
                    select(1).where(
                        and_(
                            VideoInteraction.user_id == user_id,
                            VideoInteraction.video_id == Video.id,
                            VideoInteraction.interaction_type == 1,
                        ),
                    ),
                ),
            )
        if category == "later":
            return and_(
                published,
                exists(
                    select(1).where(
                        and_(
                            VideoInteraction.user_id == user_id,
                            VideoInteraction.video_id == Video.id,
                            VideoInteraction.interaction_type == 3,
                        ),
                    ),
                ),
            )

        return published

    @staticmethod
    def resolve_sort_column(sort_by: str) -> Any:
        if sort_by == "created_at":
            return Video.created_at
        return Video.publish_date

    @staticmethod
    def time_range_predicate(time_range: str) -> list[Any]:
        """Return publish_date time range filter condition."""
        if time_range == "all":
            return []
        now = func.now()
        if time_range == "today":
            return [Video.publish_date >= func.date(now)]
        if time_range == "week":
            start = now - timedelta(days=now.extract("dow") - 1)
            return [Video.publish_date >= func.date(start)]
        if time_range == "month":
            return [
                func.extract("year", Video.publish_date) == func.extract("year", now),
                func.extract("month", Video.publish_date) == func.extract("month", now),
            ]
        if time_range == "year":
            return [func.extract("year", Video.publish_date) == func.extract("year", now)]
        return []

    @staticmethod
    def duration_predicate(duration: str) -> list[Any]:
        """Return video duration filter condition (seconds)."""
        if duration == "all":
            return []
        if duration == "short":
            return [Video.duration < 300]
        if duration == "medium":
            return [Video.duration >= 300, Video.duration <= 1800]
        if duration == "long":
            return [Video.duration > 1800]
        return []

    @staticmethod
    def content_type_predicate(content_type: str) -> list[Any]:
        """Return subscription type filter condition (requires JOIN Subscription)."""
        if content_type == "all":
            return []
        return [Subscription.type == content_type]


video_query_service = VideoQueryService()
build_video_search_clauses = video_query_service.build_video_search_clauses
build_base_video_query = video_query_service.build_base_video_query
build_video_count_source_query = video_query_service.build_video_count_source_query
category_predicate = video_query_service.category_predicate
resolve_sort_column = video_query_service.resolve_sort_column
time_range_predicate = video_query_service.time_range_predicate
duration_predicate = video_query_service.duration_predicate
content_type_predicate = video_query_service.content_type_predicate
