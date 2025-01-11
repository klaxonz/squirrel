from sqlalchemy import select

from core.database import get_session
from models.links import VideoCreator


def get_video_creator(video_id: int, creator_id: int):
    with get_session() as session:
        video_creator = session.scalars(select(VideoCreator).where(
            VideoCreator.video_id == video_id,
            VideoCreator.creator_id == creator_id)).first()
        return video_creator


def create_video_creator(video_id: int, creator_id: int):
    with get_session() as session:
        video_creator = VideoCreator(video_id=video_id, creator_id=creator_id)
        session.add(video_creator)
        session.commit()
        return video_creator
