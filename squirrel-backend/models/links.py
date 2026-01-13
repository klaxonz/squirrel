from datetime import datetime

from sqlalchemy import Integer, UniqueConstraint, Boolean, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship, foreign

from models import Base
from models.mixins.serializer import SerializerMixin



class SubscriptionVideo(Base, SerializerMixin):
    __tablename__ = "subscription_video"

    __table_args__ = (
        Index('ix_subscription_video_subscription_id', 'subscription_id'),
        Index('ix_subscription_video_video_id', 'video_id'),
    )

    subscription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )

    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        primaryjoin="Subscription.id == foreign(SubscriptionVideo.subscription_id)",
        back_populates="video_links",
        viewonly=True,
    )
    video: Mapped["Video"] = relationship(
        "Video",
        primaryjoin="Video.id == foreign(SubscriptionVideo.video_id)",
        back_populates="subscription_links",
        viewonly=True,
    )



class VideoCreator(Base):
    __tablename__ = "video_creator"

    __table_args__ = (
        Index('ix_video_creator_video_id', 'video_id'),
        Index('ix_video_creator_creator_id', 'creator_id'),
    )

    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )

    video: Mapped["Video"] = relationship(
        "Video",
        primaryjoin="Video.id == foreign(VideoCreator.video_id)",
        back_populates="creator_links",
        viewonly=True,
    )
    creator: Mapped["Creator"] = relationship(
        "Creator",
        primaryjoin="Creator.id == foreign(VideoCreator.creator_id)",
        back_populates="video_links",
        viewonly=True,
    )



class UserSubscription(Base, SerializerMixin):
    __tablename__ = "user_subscription"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    subscription: Mapped["Subscription"] = relationship(
        "Subscription",
        primaryjoin="Subscription.id == foreign(UserSubscription.subscription_id)",
        back_populates="user_subscriptions",
        viewonly=True,
    )


    __table_args__ = (
        UniqueConstraint('user_id', 'subscription_id', name='uix_user_subscription'),
        Index('ix_user_subscription_user_id', 'user_id'),
        Index('ix_user_subscription_subscription_id', 'subscription_id'),
        Index('ix_user_subscription_is_deleted', 'is_deleted'),
        Index('ix_user_subscription_user_deleted_nsfw', 'user_id', 'is_deleted', 'is_nsfw'),
        # 优化 COUNT 查询中的 JOIN：覆盖 subscription_id, user_id, is_deleted
        Index('ix_user_subscription_sub_user_deleted', 'subscription_id', 'user_id', 'is_deleted'),
    )
