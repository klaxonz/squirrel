from collections.abc import Callable, Generator

from sqlalchemy import func
from sqlalchemy.orm import Session

import domains.user.application.services.config as user_config_service
from infrastructure.database.session import get_session as _default_get_session
from domains.video.domain.models.video import Video
from domains.video.application.services.search.query import build_base_video_query as _default_build_base_video_query
from domains.video.application.services.search.query import category_predicate as _default_category_predicate

SessionFactory = Callable[[], Generator[Session, None, None]]


class VideoRandomService:
    def __init__(
        self,
        session_factory: SessionFactory | None = None,
        get_user_config=None,
        build_base_video_query=None,
        category_predicate=None,
    ):
        self._session_factory = session_factory or _default_get_session
        self._get_user_config = get_user_config or user_config_service.get_config
        self._build_base_video_query = build_base_video_query or _default_build_base_video_query
        self._category_predicate = category_predicate or _default_category_predicate

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

        base = self._build_base_video_query(
            user_id, show_nsfw, subscription_id, query, nsfw, domains,
            time_range, duration, content_type,
        )
        base = base.where(self._category_predicate(user_id, category))

        with self._session_factory() as session:
            bind = session.get_bind()
            dialect_name = getattr(getattr(bind, "dialect", None), "name", "") or ""

            if dialect_name in ("postgresql", "sqlite"):
                order_random = func.random()
            elif dialect_name in ("mysql", "mariadb"):
                order_random = func.rand()
            else:
                order_random = func.random()

            random_row = session.execute(
                base.order_by(order_random).limit(1)
            ).first()
            return random_row[0] if random_row else None


video_random_service = VideoRandomService()
get_random_video = video_random_service.get_random_video
