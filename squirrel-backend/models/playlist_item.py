from datetime import datetime

from sqlalchemy import Integer, Index, Float
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from models import Base
from models.mixins.serializer import SerializerMixin


def _playlist_join():
    from models.playlist import Playlist
    return Playlist.id == foreign(PlaylistItem.playlist_id)


def _video_join():
    from models.video import Video
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

    playlist: Mapped["Playlist"] = relationship(
        "Playlist",
        primaryjoin=_playlist_join,
        back_populates="items",
        viewonly=True,
    )
    video: Mapped["Video"] = relationship(
        "Video",
        primaryjoin=_video_join,
        viewonly=True,
    )
