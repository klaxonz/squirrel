from collections.abc import Callable, Generator

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.database import get_session as _default_get_session
from models.creator import Creator

SessionFactory = Callable[[], Generator[Session, None, None]]


class CreatorService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def get_creator_by_url(self, actor_url: str) -> Creator | None:
        with self._session_factory() as session:
            return session.scalars(select(Creator).where(Creator.url == actor_url)).first()

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


_default = CreatorService()
get_creator_by_url = _default.get_creator_by_url
create_creator = _default.create_creator
