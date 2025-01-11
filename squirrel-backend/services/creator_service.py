from sqlalchemy import select

from core.database import get_session
from models.creator import Creator


def get_creator_by_url(actor_url: str):
    with get_session() as session:
        return session.scalars(select(Creator).where(Creator.url == actor_url)).first()


def create_creator(actor_url: str, actor_name: str, actor_avatar: str):
    with get_session() as session:
        creator = Creator(
            url=actor_url,
            name=actor_name,
            avatar=actor_avatar,
            description=None,
            extra_data={}
        )
        session.add(creator)
        session.commit()
        return creator
