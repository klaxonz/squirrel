from datetime import datetime
from typing import Optional, List

from sqlalchemy import Boolean, JSON, VARCHAR, Text
from sqlalchemy.orm import mapped_column, Mapped, relationship, foreign

from models import Base
from models.mixins.serializer import SerializerMixin


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
    name: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    avatar: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    video_links: Mapped[List["VideoCreator"]] = relationship(
        "VideoCreator",
        primaryjoin=_video_links_join,
        back_populates="creator",
        viewonly=True,
    )
    videos: Mapped[List["Video"]] = relationship(
        "Video",
        secondary="video_creator",
        primaryjoin=_video_links_join,
        secondaryjoin=_videos_secondary_join,
        viewonly=True,
    )
