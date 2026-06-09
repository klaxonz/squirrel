from datetime import timedelta
from typing import Any

from sqlalchemy import and_, exists, false, func, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from models.creator import Creator
from models.links import SubscriptionVideo, UserSubscription, VideoCreator
from models.subscription import Subscription
from models.video import Video
from models.video_history import VideoHistory
from models.video_interaction import VideoInteraction
from services.nsfw_policy import resolve_effective_nsfw_filter as _default_resolve_effective_nsfw_filter
from services.search_query import escape_ilike as _escape_ilike
from services.search_query import normalize_subscription_type_term as _default_normalize_subscription_type_term
from services.search_query import parse_search_query as _default_parse_search_query
from utils import url_helper


class VideoQueryService:
    def __init__(
        self,
        resolve_effective_nsfw_filter=None,
        parse_search_query=None,
        normalize_subscription_type_term=None,
    ):
        self._resolve_effective_nsfw_filter = resolve_effective_nsfw_filter or _default_resolve_effective_nsfw_filter
        self._parse_search_query = parse_search_query or _default_parse_search_query
        self._normalize_subscription_type_term = normalize_subscription_type_term or _default_normalize_subscription_type_term

    @staticmethod
    def _contains(column: Any, term: str) -> ColumnElement[bool]:
        return column.ilike(f"%{_escape_ilike(term)}%")

    @staticmethod
    def _video_match_clause(*, video_id_column: Any, term: str) -> Any:
        video_alias = aliased(Video)
        return exists(
            select(1)
            .select_from(video_alias)
            .where(
                video_alias.id == video_id_column,
                video_alias.is_deleted.is_(False),
                or_(
                    VideoQueryService._contains(video_alias.title, term),
                    VideoQueryService._contains(video_alias.description, term),
                    VideoQueryService._contains(video_alias.url, term),
                    VideoQueryService._contains(video_alias.domain, term),
                ),
            ),
        )

    @staticmethod
    def _subscription_match_clause(*, user_id: int, video_id_column: Any = None, subscription_id_column: Any = None, term: str) -> Any:
        if subscription_id_column is not None:
            return exists(
                select(1)
                .select_from(Subscription)
                .join(
                    UserSubscription,
                    and_(
                        UserSubscription.subscription_id == Subscription.id,
                        UserSubscription.user_id == user_id,
                        UserSubscription.is_deleted.is_(False),
                    ),
                )
                .where(
                    Subscription.id == subscription_id_column,
                    Subscription.is_deleted.is_(False),
                    or_(
                        VideoQueryService._contains(Subscription.name, term),
                        VideoQueryService._contains(Subscription.url, term),
                        VideoQueryService._contains(Subscription.description, term),
                    ),
                ),
            )

        return exists(
            select(1)
            .select_from(SubscriptionVideo)
            .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
            .join(
                UserSubscription,
                and_(
                    UserSubscription.subscription_id == Subscription.id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            )
            .where(
                SubscriptionVideo.video_id == video_id_column,
                Subscription.is_deleted.is_(False),
                or_(
                    VideoQueryService._contains(Subscription.name, term),
                    VideoQueryService._contains(Subscription.url, term),
                    VideoQueryService._contains(Subscription.description, term),
                ),
            ),
        )

    def _subscription_type_clause(self, *, user_id: int, video_id_column: Any = None, subscription_id_column: Any = None, value: str) -> Any | None:
        normalized_type = self._normalize_subscription_type_term(value)
        if not normalized_type:
            return None

        if subscription_id_column is not None:
            return exists(
                select(1)
                .select_from(Subscription)
                .join(
                    UserSubscription,
                    and_(
                        UserSubscription.subscription_id == Subscription.id,
                        UserSubscription.user_id == user_id,
                        UserSubscription.is_deleted.is_(False),
                    ),
                )
                .where(
                    Subscription.id == subscription_id_column,
                    Subscription.is_deleted.is_(False),
                    Subscription.type == normalized_type,
                ),
            )

        return exists(
            select(1)
            .select_from(SubscriptionVideo)
            .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
            .join(
                UserSubscription,
                and_(
                    UserSubscription.subscription_id == Subscription.id,
                    UserSubscription.user_id == user_id,
                    UserSubscription.is_deleted.is_(False),
                ),
            )
            .where(
                SubscriptionVideo.video_id == video_id_column,
                Subscription.is_deleted.is_(False),
                Subscription.type == normalized_type,
            ),
        )

    @staticmethod
    def _creator_match_clause(*, video_id_column: Any, term: str) -> Any:
        return exists(
            select(1)
            .select_from(VideoCreator)
            .join(Creator, Creator.id == VideoCreator.creator_id)
            .where(
                VideoCreator.video_id == video_id_column,
                Creator.is_deleted.is_(False),
                or_(
                    VideoQueryService._contains(Creator.name, term),
                    VideoQueryService._contains(Creator.url, term),
                    VideoQueryService._contains(Creator.description, term),
                ),
            ),
        )

    def build_video_search_clauses(self, *, user_id: int, query: str | None, video_id_column: Any, subscription_id_column: Any = None) -> list[Any]:
        parsed_query = self._parse_search_query(query)
        if not parsed_query.has_terms:
            return []

        clauses = []

        for term in parsed_query.text_terms:
            clauses.append(
                or_(
                    self._video_match_clause(video_id_column=video_id_column, term=term),
                    self._subscription_match_clause(
                        user_id=user_id,
                        video_id_column=video_id_column,
                        subscription_id_column=subscription_id_column,
                        term=term,
                    ),
                    self._creator_match_clause(video_id_column=video_id_column, term=term),
                ),
            )

        for term in parsed_query.get("title"):
            video_alias = aliased(Video)
            clauses.append(
                exists(
                    select(1)
                    .select_from(video_alias)
                    .where(
                        video_alias.id == video_id_column,
                        video_alias.is_deleted.is_(False),
                        VideoQueryService._contains(video_alias.title, term),
                    ),
                ),
            )

        for term in parsed_query.get("url"):
            video_alias = aliased(Video)
            clauses.append(
                exists(
                    select(1)
                    .select_from(video_alias)
                    .where(
                        video_alias.id == video_id_column,
                        video_alias.is_deleted.is_(False),
                        VideoQueryService._contains(video_alias.url, term),
                    ),
                ),
            )

        for term in parsed_query.get("domain"):
            video_alias = aliased(Video)
            clauses.append(
                exists(
                    select(1)
                    .select_from(video_alias)
                    .where(
                        video_alias.id == video_id_column,
                        video_alias.is_deleted.is_(False),
                        VideoQueryService._contains(video_alias.domain, term),
                    ),
                ),
            )

        for term in parsed_query.get("description"):
            clauses.append(
                or_(
                    self._video_match_clause(video_id_column=video_id_column, term=term),
                    self._subscription_match_clause(
                        user_id=user_id,
                        video_id_column=video_id_column,
                        subscription_id_column=subscription_id_column,
                        term=term,
                    ),
                    self._creator_match_clause(video_id_column=video_id_column, term=term),
                ),
            )

        for term in parsed_query.get("subscription"):
            clauses.append(
                self._subscription_match_clause(
                    user_id=user_id,
                    video_id_column=video_id_column,
                    subscription_id_column=subscription_id_column,
                    term=term,
                ),
            )

        for term in parsed_query.get("creator"):
            clauses.append(self._creator_match_clause(video_id_column=video_id_column, term=term))

        for term in parsed_query.get("type"):
            type_clause = self._subscription_type_clause(
                user_id=user_id,
                video_id_column=video_id_column,
                subscription_id_column=subscription_id_column,
                value=term,
            )
            if type_clause is not None:
                clauses.append(type_clause)

        return clauses

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


_default = VideoQueryService()
build_video_search_clauses = _default.build_video_search_clauses
build_base_video_query = _default.build_base_video_query
build_video_count_source_query = _default.build_video_count_source_query
category_predicate = _default.category_predicate
resolve_sort_column = _default.resolve_sort_column
time_range_predicate = _default.time_range_predicate
duration_predicate = _default.duration_predicate
content_type_predicate = _default.content_type_predicate
