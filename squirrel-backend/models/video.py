from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, VARCHAR, Boolean, DateTime, Index, Integer, Text, text
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from models import Base
from models.mixins.serializer import SerializerMixin

if TYPE_CHECKING:
    from models.creator import Creator
    from models.links import SubscriptionVideo, VideoCreator
    from models.playlist_item import PlaylistItem
    from models.subscription import Subscription
    from models.video_clip_marker import VideoClipMarker
    from models.video_history import VideoHistory
    from models.video_interaction import VideoInteraction


def _subscription_links_join():
    from models.links import SubscriptionVideo
    return Video.id == foreign(SubscriptionVideo.video_id)


def _subscriptions_secondary_join():
    from models.links import SubscriptionVideo
    from models.subscription import Subscription
    return Subscription.id == foreign(SubscriptionVideo.subscription_id)


def _creator_links_join():
    from models.links import VideoCreator
    return Video.id == foreign(VideoCreator.video_id)


def _creators_secondary_join():
    from models.creator import Creator
    from models.links import VideoCreator
    return Creator.id == foreign(VideoCreator.creator_id)


def _histories_join():
    from models.video_history import VideoHistory
    return Video.id == foreign(VideoHistory.video_id)


def _interactions_join():
    from models.video_interaction import VideoInteraction
    return Video.id == foreign(VideoInteraction.video_id)


def _clip_markers_join():
    from models.video_clip_marker import VideoClipMarker
    return Video.id == foreign(VideoClipMarker.video_id)


def _playlist_items_join():
    from models.playlist_item import PlaylistItem
    return Video.id == foreign(PlaylistItem.video_id)


class Video(Base, SerializerMixin):
    __tablename__ = "video"

    __table_args__ = (
        Index("ix_video_title", "title"),
        Index("ix_video_deleted_publish_date", "is_deleted", "publish_date"),
        Index("ix_video_deleted_created_at", "is_deleted", "created_at"),
        Index("ix_video_active_id_publish_date", "id", "publish_date", postgresql_where=text("is_deleted = false")),
        Index("ux_video_url", "url", unique=True),
        Index("ix_video_domain", "domain"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    domain: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration: Mapped[int | None] = mapped_column(Integer, nullable=True)
    thumbnail: Mapped[str | None] = mapped_column(VARCHAR(2048), nullable=True)
    publish_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )

    subscription_links: Mapped[list[SubscriptionVideo]] = relationship(
        "SubscriptionVideo",
        primaryjoin=_subscription_links_join,
        back_populates="video",
        viewonly=True,
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        "Subscription",
        secondary="subscription_video",
        primaryjoin=_subscription_links_join,
        secondaryjoin=_subscriptions_secondary_join,
        viewonly=True,
    )
    creator_links: Mapped[list[VideoCreator]] = relationship(
        "VideoCreator",
        primaryjoin=_creator_links_join,
        back_populates="video",
        viewonly=True,
    )
    creators: Mapped[list[Creator]] = relationship(
        "Creator",
        secondary="video_creator",
        primaryjoin=_creator_links_join,
        secondaryjoin=_creators_secondary_join,
        viewonly=True,
    )
    histories: Mapped[list[VideoHistory]] = relationship(
        "VideoHistory",
        primaryjoin=_histories_join,
        back_populates="video",
        viewonly=True,
    )
    interactions: Mapped[list[VideoInteraction]] = relationship(
        "VideoInteraction",
        primaryjoin=_interactions_join,
        back_populates="video",
        viewonly=True,
    )
    clip_markers: Mapped[list[VideoClipMarker]] = relationship(
        "VideoClipMarker",
        primaryjoin=_clip_markers_join,
        back_populates="video",
        viewonly=True,
    )
    playlist_items: Mapped[list[PlaylistItem]] = relationship(
        "PlaylistItem",
        primaryjoin=_playlist_items_join,
        back_populates="video",
        viewonly=True,
    )
