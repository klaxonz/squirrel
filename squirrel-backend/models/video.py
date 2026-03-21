from datetime import datetime
from typing import Optional, List

from sqlalchemy import Integer, Boolean, JSON, VARCHAR, Text, DateTime, Index, text
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from models import Base
from models.mixins.serializer import SerializerMixin


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


class Video(Base, SerializerMixin):
    __tablename__ = "video"

    __table_args__ = (
        Index('ix_video_title', 'title'),
        Index('ix_video_deleted_publish_date', 'is_deleted', 'publish_date'),
        Index('ix_video_deleted_created_at', 'is_deleted', 'created_at'),
        Index('ix_video_active_id_publish_date', 'id', 'publish_date', postgresql_where=text('is_deleted = false')),
        Index('ux_video_url', 'url', unique=True),
        Index('ix_video_domain', 'domain'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(VARCHAR(255), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    publish_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    subscription_links: Mapped[List["SubscriptionVideo"]] = relationship(
        "SubscriptionVideo",
        primaryjoin=_subscription_links_join,
        back_populates="video",
        viewonly=True,
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        secondary="subscription_video",
        primaryjoin=_subscription_links_join,
        secondaryjoin=_subscriptions_secondary_join,
        viewonly=True,
    )
    creator_links: Mapped[List["VideoCreator"]] = relationship(
        "VideoCreator",
        primaryjoin=_creator_links_join,
        back_populates="video",
        viewonly=True,
    )
    creators: Mapped[List["Creator"]] = relationship(
        "Creator",
        secondary="video_creator",
        primaryjoin=_creator_links_join,
        secondaryjoin=_creators_secondary_join,
        viewonly=True,
    )
    histories: Mapped[List["VideoHistory"]] = relationship(
        "VideoHistory",
        primaryjoin=_histories_join,
        back_populates="video",
        viewonly=True,
    )
    interactions: Mapped[List["VideoInteraction"]] = relationship(
        "VideoInteraction",
        primaryjoin=_interactions_join,
        back_populates="video",
        viewonly=True,
    )
