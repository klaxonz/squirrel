from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import VARCHAR, Float, Index, Integer, Text
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from infrastructure.database.base import Base
from infrastructure.database.mixins import SerializerMixin

if TYPE_CHECKING:
    from domains.video.domain.models.video import Video


def _video_join():
    from domains.video.domain.models.video import Video

    return Video.id == foreign(VideoClipMarker.video_id)


class VideoClipMarker(Base, SerializerMixin):
    __tablename__ = 'video_clip_marker'

    __table_args__ = (
        Index('ix_video_clip_marker_user_video', 'user_id', 'video_id'),
        Index('ix_video_clip_marker_user_created_at', 'user_id', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    preview_image_url: Mapped[str | None] = mapped_column(VARCHAR(1024), nullable=True)
    start_time: Mapped[float] = mapped_column(Float, default=0.0)
    end_time: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    video: Mapped[Video] = relationship(
        'Video',
        primaryjoin=_video_join,
        back_populates='clip_markers',
        viewonly=True,
    )
