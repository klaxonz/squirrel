from collections.abc import Callable, Generator
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

import domains.user.application.services.config as user_config_service
from infrastructure.database.session import get_session as _default_get_session
from domains.video.domain.models.video_history import VideoHistory
from domains.video.interfaces.dto.video_history import HistoryCreate
from domains.video.application.services.history.query import list_history_page
from domains.video.application.services.history.serialization import serialize_history_items
from domains.video.application.services.history.updates import apply_history_updates
from domains.video.application.services.moderation.nsfw_policy import resolve_effective_nsfw_filter

SessionFactory = Callable[[], Generator[Session, None, None]]


class VideoHistoryService:
    def __init__(self, session_factory: SessionFactory | None = None, get_user_config=None):
        self._session_factory = session_factory or _default_get_session
        self._get_user_config = get_user_config or user_config_service.get_config

    def update_history(self, user_id: int, data: HistoryCreate):
        with self._session_factory() as session:
            apply_history_updates(session, user_id, [data])
            session.commit()

    def batch_update_histories(self, user_id: int, reports: list[HistoryCreate]) -> None:
        with self._session_factory() as session:
            apply_history_updates(session, user_id, reports)
            session.commit()

    def list_histories(self, user_id: int, filters: dict, page: int, page_size: int) -> dict[str, Any]:
        user_config = self._get_user_config(user_id)
        show_nsfw = user_config.get('showNsfw', False)
        effective_nsfw = resolve_effective_nsfw_filter(filters.get('nsfw', 'all'), show_nsfw)

        with self._session_factory() as session:
            histories, total = list_history_page(
                session,
                user_id=user_id,
                filters=filters,
                page=page,
                page_size=page_size,
                effective_nsfw=effective_nsfw,
            )

            if not histories:
                return {
                    'items': [],
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                }

            return {
                'items': serialize_history_items(session, user_id, histories),
                'total': total,
                'page': page,
                'page_size': page_size,
            }

    def get_videos_by_ids(self, user_id: int, video_ids: list[int]) -> list[VideoHistory]:
        with self._session_factory() as session:
            videos = session.scalars(
                select(VideoHistory).where(
                    VideoHistory.user_id == user_id,
                    VideoHistory.video_id.in_(video_ids),
                ),
            ).all()
            return videos

    def get_video_history(self, user_id: int, video_id: int) -> VideoHistory | None:
        with self._session_factory() as session:
            video_history = session.scalars(
                select(VideoHistory).where(
                    VideoHistory.user_id == user_id,
                    VideoHistory.video_id == video_id,
                ),
            ).first()
            return video_history

    def delete_history(self, user_id: int, history_id: int) -> int:
        with self._session_factory() as session:
            query_result = session.execute(
                delete(VideoHistory).where(
                    VideoHistory.id == history_id,
                    VideoHistory.user_id == user_id,
                ),
            )
            session.commit()
            return query_result.rowcount

    def clear_histories(self, user_id: int, video_ids: list[int] | None = None):
        with self._session_factory() as session:
            conditions = [VideoHistory.user_id == user_id]

            if video_ids:
                conditions.append(VideoHistory.video_id.in_(video_ids))

            query_result = session.execute(
                delete(VideoHistory).where(*conditions),
            )
            session.commit()
            return query_result.rowcount
