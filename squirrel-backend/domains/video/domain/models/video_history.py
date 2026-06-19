from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from infrastructure.database.base import Base
from infrastructure.database.mixins import SerializerMixin

if TYPE_CHECKING:
    from domains.video.domain.models.video import Video


def _video_join():
    from domains.video.domain.models.video import Video

    return Video.id == foreign(VideoHistory.video_id)


class VideoHistory(Base, SerializerMixin):
    __tablename__ = 'video_history'

    __table_args__ = (
        Index('ux_video_history_user_video', 'user_id', 'video_id', unique=True),
        Index('ix_video_history_video_id', 'video_id'),
        Index('ix_video_history_user_end_time', 'user_id', 'end_time'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    duration: Mapped[float] = mapped_column(Float)
    watch_duration: Mapped[int] = mapped_column(Integer, default=0)
    last_position: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    video: Mapped[Video] = relationship(
        'Video',
        primaryjoin=_video_join,
        back_populates='histories',
        viewonly=True,
    )
