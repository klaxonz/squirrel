from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, VARCHAR, Boolean, Text
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from models import Base
from models.mixins.serializer import SerializerMixin

if TYPE_CHECKING:
    from models.links import VideoCreator
    from models.video import Video


def _video_links_join():
    from models.links import VideoCreator
    return Creator.id == foreign(VideoCreator.creator_id)


def _videos_secondary_join():
    from models.links import VideoCreator
    from models.video import Video
    return Video.id == foreign(VideoCreator.video_id)


class Creator(Base, SerializerMixin):
    __tablename__ = "creator"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    avatar: Mapped[str | None] = mapped_column(VARCHAR(2048), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    video_links: Mapped[list[VideoCreator]] = relationship(
        "VideoCreator",
        primaryjoin=_video_links_join,
        back_populates="creator",
        viewonly=True,
    )
    videos: Mapped[list[Video]] = relationship(
        "Video",
        secondary="video_creator",
        primaryjoin=_video_links_join,
        secondaryjoin=_videos_secondary_join,
        viewonly=True,
    )
