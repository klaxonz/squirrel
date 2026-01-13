from datetime import datetime
from typing import Optional, List
from sqlalchemy import Integer, Boolean, JSON, VARCHAR, Text, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign
from models import Base
from models.mixins.serializer import SerializerMixin



class Video(Base, SerializerMixin):
    __tablename__ = "video"

    __table_args__ = (
        Index('ix_video_title', 'title'),
        Index('ix_video_deleted_publish_date',  'is_deleted', 'publish_date'),
        Index('ix_video_deleted_created_at', 'is_deleted', 'created_at'),
        Index('ux_video_url', 'url', unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(512), nullable=False)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    thumbnail: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    publish_date: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    subscription_links: Mapped[List["SubscriptionVideo"]] = relationship(
        "SubscriptionVideo",
        primaryjoin="Video.id == foreign(SubscriptionVideo.video_id)",
        back_populates="video",
        viewonly=True,
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        secondary="subscription_video",
        primaryjoin="Video.id == foreign(SubscriptionVideo.video_id)",
        secondaryjoin="Subscription.id == foreign(SubscriptionVideo.subscription_id)",
        viewonly=True,
    )
    creator_links: Mapped[List["VideoCreator"]] = relationship(
        "VideoCreator",
        primaryjoin="Video.id == foreign(VideoCreator.video_id)",
        back_populates="video",
        viewonly=True,
    )
    creators: Mapped[List["Creator"]] = relationship(
        "Creator",
        secondary="video_creator",
        primaryjoin="Video.id == foreign(VideoCreator.video_id)",
        secondaryjoin="Creator.id == foreign(VideoCreator.creator_id)",
        viewonly=True,
    )
    histories: Mapped[List["VideoHistory"]] = relationship(
        "VideoHistory",
        primaryjoin="Video.id == foreign(VideoHistory.video_id)",
        back_populates="video",
        viewonly=True,
    )
    interactions: Mapped[List["VideoInteraction"]] = relationship(
        "VideoInteraction",
        primaryjoin="Video.id == foreign(VideoInteraction.video_id)",
        back_populates="video",
        viewonly=True,
    )

