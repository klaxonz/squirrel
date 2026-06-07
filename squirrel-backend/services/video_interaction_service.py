
from sqlalchemy import select

from core.database import get_session
from models.video_interaction import VideoInteraction


def save_or_update_video_interaction(user_id: int, video_id: int, interaction_type: int) -> VideoInteraction:
    with get_session() as session:
        video_interaction = session.scalars(
            select(VideoInteraction).where(
                VideoInteraction.video_id == video_id,
                VideoInteraction.user_id == user_id,
            ),
        ).first()
        if video_interaction:
            video_interaction.interaction_type = interaction_type
            session.commit()
            session.refresh(video_interaction)
            return video_interaction
        video_interaction = VideoInteraction(
            video_id=video_id,
            user_id=user_id,
            interaction_type=interaction_type,
        )
        session.add(video_interaction)
        session.commit()
        session.refresh(video_interaction)
        return video_interaction


def get_video_interaction(user_id: int, video_id: int) -> VideoInteraction | None:
    with get_session() as session:
        video_interaction = session.scalars(
            select(VideoInteraction).where(
                VideoInteraction.video_id == video_id,
                VideoInteraction.user_id == user_id,
            ),
        ).first()
        return video_interaction


def delete_video_interaction(user_id: int, video_id: int) -> None:
    with get_session() as session:
        video_interaction = session.scalars(
            select(VideoInteraction).where(
                VideoInteraction.video_id == video_id,
                VideoInteraction.user_id == user_id,
            ),
        ).first()
        if video_interaction:
            session.delete(video_interaction)
            session.commit()
