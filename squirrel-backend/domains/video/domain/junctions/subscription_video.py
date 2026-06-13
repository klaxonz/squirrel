"""SubscriptionVideo junction table - owned by video domain."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Index, Integer
from sqlalchemy.orm import Mapped, foreign, mapped_column, relationship

from shared_kernel.domain.base import Base
from shared_kernel.domain.mixins import SerializerMixin

if TYPE_CHECKING:
    from domains.subscription.domain.models.subscription import Subscription
    from domains.video.domain.models.video import Video


def _subscription_video_subscription_join():
    from domains.subscription.domain.models.subscription import Subscription
    return Subscription.id == foreign(SubscriptionVideo.subscription_id)


def _subscription_video_video_join():
    from domains.video.domain.models.video import Video
    return Video.id == foreign(SubscriptionVideo.video_id)


class SubscriptionVideo(Base, SerializerMixin):
    __tablename__ = "subscription_video"

    __table_args__ = (
        Index("ix_subscription_video_subscription_id", "subscription_id"),
        Index("ix_subscription_video_video_id", "video_id"),
    )

    subscription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())

    subscription: Mapped[Subscription] = relationship(
        "Subscription",
        primaryjoin=_subscription_video_subscription_join,
        back_populates="video_links",
        viewonly=True,
    )
    video: Mapped[Video] = relationship(
        "Video",
        primaryjoin=_subscription_video_video_join,
        back_populates="subscription_links",
        viewonly=True,
    )