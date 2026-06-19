from collections.abc import Callable, Generator
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

import domains.user.application.services.config as user_config_service
from domains.subscription.domain.junctions.user_subscription import UserSubscription
from domains.subscription.domain.models.subscription import Subscription
from domains.video.application.services.listing.query_filters import (
    feed_category_predicate as _default_category_predicate,
)
from domains.video.application.services.moderation.nsfw_policy import resolve_effective_nsfw_filter
from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
from domains.video.domain.junctions.subscription_video import SubscriptionVideo
from domains.video.domain.models.video import Video
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]


class VideoRandomService:
    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        get_user_config=None,
        category_predicate=None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._get_user_config = get_user_config or user_config_service.get_config
        self._category_predicate = category_predicate or _default_category_predicate

    @staticmethod
    def _has_structural_filter(
        domains: list[str] | None, time_range: str, duration: str,
    ) -> bool:
        if time_range != 'all' or duration != 'all':
            return True
        return bool(domains)

    @classmethod
    def _recall_video_ids(
        cls,
        query: str | None,
        domains: list[str] | None,
        time_range: str,
        duration: str,
    ) -> list[int] | None:
        """有搜索词或结构化过滤时用 Meili 召回;否则返回 None 走全量随机。"""
        has_query = bool(query and query.strip())
        if not has_query and not cls._has_structural_filter(domains, time_range, duration):
            return None
        if not settings.meili.url:
            return [] if has_query else None
        try:
            return get_meili_video_indexer().recall(
                query or '',
                domains=domains,
                time_range=time_range,
                duration=duration,
            )
        except Exception:
            return [] if has_query else None

    def get_random_video(
            self,
            user_id: int,
            category: str | None = None,
            subscription_id: int | None = None,
            nsfw: str = "all",
            domains: list[str] | None = None,
            query: str | None = None,
            time_range: str = "all",
            duration: str = "all",
            content_type: str = "all",
    ) -> Video | None:
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get("showNsfw", False)
        effective_nsfw = resolve_effective_nsfw_filter(nsfw, show_nsfw)

        recalled_ids = self._recall_video_ids(query, domains, time_range, duration)

        # 召回为空(有搜索词但无匹配)→ 直接无结果
        if recalled_ids is not None and not recalled_ids:
            return None

        with self._session_factory() as session:
            conditions: list[Any] = [
                UserSubscription.user_id == user_id,
                UserSubscription.is_deleted.is_(False),
                Subscription.is_deleted.is_(False),
                Video.is_deleted.is_(False),
            ]

            if effective_nsfw == 'blocked':
                return None
            elif effective_nsfw == 'yes':
                conditions.append(UserSubscription.is_nsfw.is_(True))
            elif effective_nsfw == 'no':
                conditions.append(UserSubscription.is_nsfw.is_(False))

            if subscription_id:
                conditions.append(Subscription.id == subscription_id)

            if content_type != 'all':
                conditions.append(Subscription.type == content_type)

            if recalled_ids is not None:
                conditions.append(Video.id.in_(recalled_ids))

            base_query = (
                select(Video)
                .select_from(Video)
                .join(SubscriptionVideo, SubscriptionVideo.video_id == Video.id)
                .join(UserSubscription, UserSubscription.subscription_id == SubscriptionVideo.subscription_id)
                .join(Subscription, Subscription.id == SubscriptionVideo.subscription_id)
                .where(*conditions)
            )

            # category(read/unread/liked/later/preview)走 feed_category_predicate EXISTS
            if category:
                base_query = base_query.where(
                    self._category_predicate(
                        user_id,
                        category,
                        video_id_column=Video.id,
                        publish_date_column=Video.publish_date,
                    )
                )

            random_row = session.execute(
                base_query.order_by(func.random()).limit(1)
            ).first()
            return random_row[0] if random_row else None


video_random_service = VideoRandomService()
get_random_video = video_random_service.get_random_video
