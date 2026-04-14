from datetime import datetime

from sqlalchemy import Integer, VARCHAR, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from models import Base
from models.mixins.serializer import SerializerMixin


def _items_join():
    from models.playlist_item import PlaylistItem
    return Playlist.id == foreign(PlaylistItem.playlist_id)


class Playlist(Base, SerializerMixin):
    __tablename__ = 'playlist'

    __table_args__ = (
        Index('ix_playlist_user_created_at', 'user_id', 'created_at'),
        Index('ix_playlist_user_name', 'user_id', 'name'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(255), nullable=False)
    description: Mapped[str | None] = mapped_column(VARCHAR(512), nullable=True)
    is_default: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    items: Mapped[list["PlaylistItem"]] = relationship(
        "PlaylistItem",
        primaryjoin=_items_join,
        back_populates="playlist",
        viewonly=True,
    )
