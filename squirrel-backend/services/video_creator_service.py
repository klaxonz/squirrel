from collections.abc import Callable, Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from models.links import VideoCreator

SessionFactory = Callable[[], Generator[Session, None, None]]


class VideoCreatorService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def get_video_creator(self, video_id: int, creator_id: int) -> VideoCreator | None:
        with self._session_factory() as session:
            video_creator = session.scalars(select(VideoCreator).where(
                VideoCreator.video_id == video_id,
                VideoCreator.creator_id == creator_id)).first()
            return video_creator

    def create_video_creator(self, video_id: int, creator_id: int) -> VideoCreator:
        with self._session_factory() as session:
            video_creator = VideoCreator(video_id=video_id, creator_id=creator_id)
            session.add(video_creator)
            session.commit()
            return video_creator


_default = VideoCreatorService()
get_video_creator = _default.get_video_creator
create_video_creator = _default.create_video_creator
