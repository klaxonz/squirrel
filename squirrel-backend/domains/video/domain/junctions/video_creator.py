"""VideoCreator junction table - owned by video domain."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from infrastructure.database.base import Base

if TYPE_CHECKING:
    from domains.video.domain.models.creator import Creator
    from domains.video.domain.models.video import Video


def _video_creator_video_join():
    from domains.video.domain.models.video import Video
    return Video.id == foreign(VideoCreator.video_id)


def _video_creator_creator_join():
    from domains.video.domain.models.creator import Creator
    return Creator.id == foreign(VideoCreator.creator_id)


class VideoCreator(Base):
    __tablename__ = "video_creator"

    __table_args__ = (
        Index("ix_video_creator_video_id", "video_id"),
        Index("ix_video_creator_creator_id", "creator_id"),
    )

    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())

    video: Mapped[Video] = relationship(
        "Video",
        primaryjoin=_video_creator_video_join,
        back_populates="creator_links",
        viewonly=True,
    )
    creator: Mapped[Creator] = relationship(
        "Creator",
        primaryjoin=_video_creator_creator_join,
        back_populates="video_links",
        viewonly=True,
    )
