from __future__ import annotations

from typing import Any

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.orm import aliased
from sqlalchemy.sql.elements import ColumnElement

from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.video.domain.junctions.video_creator import VideoCreator
from infrastructure.search.query import escape_ilike
from infrastructure.search.query import normalize_subscription_type_term as default_normalize_subscription_type_term
from infrastructure.search.query import parse_search_query as default_parse_search_query
from domains.subscription.domain.models.subscription import Subscription
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video


class VideoSearchQueryBuilder:
    def __init__(
        self,
        *,
        parse_search_query=None,
        normalize_subscription_type_term=None,
    ):
        self._parse_search_query = parse_search_query or default_parse_search_query
        self._normalize_subscription_type_term = normalize_subscription_type_term or default_normalize_subscription_type_term

    @staticmethod
    def contains(column: Any, term: str) -> ColumnElement[bool]:
        return column.ilike(f"%{escape_ilike(term)}%")

    @staticmethod
    def video_match_clause(*, video_id_column: Any, term: str) -> Any:
        video_alias = aliased(Video)
        return exists(
            select(1)
            .select_from(video_alias)
            .where(
                video_alias.id == video_id_column,
                video_alias.is_deleted.is_(False),
                or_(
                    VideoSearchQueryBuilder.contains(video_alias.title, term),
                    VideoSearchQueryBuilder.contains(video_alias.description, term),
                    VideoSearchQueryBuilder.contains(video_alias.url, term),
                    VideoSearchQueryBuilder.contains(video_alias.domain, term),
                ),
            ),
        )

    @staticmethod
    def subscription_match_clause(*, user_id: int, video_id_column: Any = None, subscription_id_column: Any = None, term: str) -> Any:
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
                        VideoSearchQueryBuilder.contains(Subscription.name, term),
                        VideoSearchQueryBuilder.contains(Subscription.url, term),
                        VideoSearchQueryBuilder.contains(Subscription.description, term),
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
                    VideoSearchQueryBuilder.contains(Subscription.name, term),
                    VideoSearchQueryBuilder.contains(Subscription.url, term),
                    VideoSearchQueryBuilder.contains(Subscription.description, term),
                ),
            ),
        )

    def subscription_type_clause(self, *, user_id: int, video_id_column: Any = None, subscription_id_column: Any = None, value: str) -> Any | None:
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
    def creator_match_clause(*, video_id_column: Any, term: str) -> Any:
        return exists(
            select(1)
            .select_from(VideoCreator)
            .join(Creator, Creator.id == VideoCreator.creator_id)
            .where(
                VideoCreator.video_id == video_id_column,
                Creator.is_deleted.is_(False),
                or_(
                    VideoSearchQueryBuilder.contains(Creator.name, term),
                    VideoSearchQueryBuilder.contains(Creator.url, term),
                    VideoSearchQueryBuilder.contains(Creator.description, term),
                ),
            ),
        )

    def build_clauses(self, *, user_id: int, query: str | None, video_id_column: Any, subscription_id_column: Any = None) -> list[Any]:
        parsed_query = self._parse_search_query(query)
        if not parsed_query.has_terms:
            return []

        clauses = []

        for term in parsed_query.text_terms:
            clauses.append(
                or_(
                    self.video_match_clause(video_id_column=video_id_column, term=term),
                    self.subscription_match_clause(
                        user_id=user_id,
                        video_id_column=video_id_column,
                        subscription_id_column=subscription_id_column,
                        term=term,
                    ),
                    self.creator_match_clause(video_id_column=video_id_column, term=term),
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
                        VideoSearchQueryBuilder.contains(video_alias.title, term),
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
                        VideoSearchQueryBuilder.contains(video_alias.url, term),
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
                        VideoSearchQueryBuilder.contains(video_alias.domain, term),
                    ),
                ),
            )

        for term in parsed_query.get("description"):
            clauses.append(
                or_(
                    self.video_match_clause(video_id_column=video_id_column, term=term),
                    self.subscription_match_clause(
                        user_id=user_id,
                        video_id_column=video_id_column,
                        subscription_id_column=subscription_id_column,
                        term=term,
                    ),
                    self.creator_match_clause(video_id_column=video_id_column, term=term),
                ),
            )

        for term in parsed_query.get("subscription"):
            clauses.append(
                self.subscription_match_clause(
                    user_id=user_id,
                    video_id_column=video_id_column,
                    subscription_id_column=subscription_id_column,
                    term=term,
                ),
            )

        for term in parsed_query.get("creator"):
            clauses.append(self.creator_match_clause(video_id_column=video_id_column, term=term))

        for term in parsed_query.get("type"):
            type_clause = self.subscription_type_clause(
                user_id=user_id,
                video_id_column=video_id_column,
                subscription_id_column=subscription_id_column,
                value=term,
            )
            if type_clause is not None:
                clauses.append(type_clause)

        return clauses


video_search_query_builder = VideoSearchQueryBuilder()
build_video_search_clauses = video_search_query_builder.build_clauses
