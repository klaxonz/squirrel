from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from infrastructure.database.base import Base
from infrastructure.database.mixins import SerializerMixin

if TYPE_CHECKING:
    from domains.playlist.domain.models.playlist import Playlist
    from domains.video.domain.models.video import Video


def _playlist_join():
    from domains.playlist.domain.models.playlist import Playlist

    return Playlist.id == foreign(PlaylistItem.playlist_id)


def _video_join():
    from domains.video.domain.models.video import Video

    return Video.id == foreign(PlaylistItem.video_id)


class PlaylistItem(Base, SerializerMixin):
    __tablename__ = 'playlist_item'

    __table_args__ = (
        Index('ix_playlist_item_playlist_position', 'playlist_id', 'position'),
        Index('ix_playlist_item_user_video', 'user_id', 'video_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    playlist_id: Mapped[int] = mapped_column(Integer, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0)
    added_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())

    playlist: Mapped[Playlist] = relationship(
        'Playlist',
        primaryjoin=_playlist_join,
        back_populates='items',
        viewonly=True,
    )
    video: Mapped[Video] = relationship(
        'Video',
        primaryjoin=_video_join,
        viewonly=True,
    )
