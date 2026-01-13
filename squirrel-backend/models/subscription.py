from datetime import datetime
from typing import Optional, List

from sqlalchemy.types import JSON
from sqlalchemy import Integer, VARCHAR, Text, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from models import Base
from models.mixins.serializer import SerializerMixin



class ContentType:
    CHANNEL = "CHANNEL"
    PLAYLIST = "PLAYLIST"
    ACTRESS = "ACTRESS"
    MOVIE = "MOVIE"
    TV_SERIES = "TV_SERIES"
    ACTOR = "ACTOR"


class Subscription(Base, SerializerMixin):
    __tablename__ = "subscription"

    __table_args__ = (
        Index('ix_subscription_is_deleted', 'is_deleted'),
        Index('ix_subscription_type', 'type'),
        # 优化 COUNT 查询中的 JOIN：先过滤 is_deleted，再用 id 做 JOIN
        Index('ix_subscription_deleted_id', 'is_deleted', 'id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)
    name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    avatar: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_videos: Mapped[int] = mapped_column(Integer, default=0)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON, default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    video_links: Mapped[List["SubscriptionVideo"]] = relationship(
        "SubscriptionVideo",
        primaryjoin="Subscription.id == foreign(SubscriptionVideo.subscription_id)",
        back_populates="subscription",
        viewonly=True,
    )
    videos: Mapped[List["Video"]] = relationship(
        "Video",
        secondary="subscription_video",
        primaryjoin="Subscription.id == foreign(SubscriptionVideo.subscription_id)",
        secondaryjoin="Video.id == foreign(SubscriptionVideo.video_id)",
        viewonly=True,
    )
    user_subscriptions: Mapped[List["UserSubscription"]] = relationship(
        "UserSubscription",
        primaryjoin="Subscription.id == foreign(UserSubscription.subscription_id)",
        back_populates="subscription",
        viewonly=True,
    )

