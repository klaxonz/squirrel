from collections.abc import Callable, Generator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domains.video.domain.junctions.video_creator import VideoCreator
from domains.video.domain.models.creator import Creator
from domains.video.domain.models.video import Video
from domains.video.interfaces.dto.video_responses import serialize_creator
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]


class CreatorService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def get_creator_by_url(self, actor_url: str) -> Creator | None:
        with self._session_factory() as session:
            return session.scalars(select(Creator).where(Creator.url == actor_url)).first()

    def get_creator_by_id(self, creator_id: int) -> Creator | None:
        with self._session_factory() as session:
            return session.scalars(
                select(Creator).where(
                    Creator.id == creator_id,
                    Creator.is_deleted.is_(False),
                )
            ).first()

    def count_videos_for_creator(self, creator_id: int) -> int:
        with self._session_factory() as session:
            count = session.scalar(
                select(func.count())
                .select_from(VideoCreator)
                .join(Video, Video.id == VideoCreator.video_id)
                .where(
                    VideoCreator.creator_id == creator_id,
                    Video.is_deleted.is_(False),
                )
            )
            return int(count or 0)

    def get_creator_detail(self, creator_id: int) -> dict | None:
        creator = self.get_creator_by_id(creator_id)
        if not creator:
            return None
        payload = serialize_creator(creator)
        payload['total_videos'] = self.count_videos_for_creator(creator_id)
        return payload

    def create_creator(self, actor_url: str, actor_name: str, actor_avatar: str) -> Creator:
        with self._session_factory() as session:
            creator = Creator(
                url=actor_url,
                name=actor_name,
                avatar=actor_avatar,
                description=None,
                extra_data={},
            )
            session.add(creator)
            session.commit()
            return creator
