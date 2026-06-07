from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from models import Base
from models.mixins.serializer import SerializerMixin

if TYPE_CHECKING:
    from models.video import Video


def _video_join():
    from models.video import Video
    return Video.id == foreign(VideoInteraction.video_id)


class VideoInteraction(Base, SerializerMixin):
    __tablename__ = "video_interaction"

    __table_args__ = (
        Index("ix_video_interaction_user_video", "user_id", "video_id"),
        Index("ix_video_interaction_user_type_video", "user_id", "interaction_type", "video_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    interaction_type: Mapped[int] = mapped_column(Integer, nullable=False, comment="1: like, 2: dislike")
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    video: Mapped[Video] = relationship(
        "Video",
        primaryjoin=_video_join,
        back_populates="interactions",
        viewonly=True,
    )
