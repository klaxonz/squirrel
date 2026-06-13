from datetime import datetime

from sqlalchemy import VARCHAR, Boolean, DateTime, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.base import Base
from shared_kernel.domain.mixins import SerializerMixin


class UserVideoFeed(Base, SerializerMixin):
    __tablename__ = "user_video_feed"

    __table_args__ = (
        UniqueConstraint("user_id", "subscription_id", "video_id", name="uix_user_video_feed_user_sub_video"),
        Index("ix_user_video_feed_user_publish_video", "user_id", "publish_date", "video_id"),
        Index("ix_user_video_feed_user_created_video", "user_id", "video_created_at", "video_id"),
        Index("ix_user_video_feed_user_sub_publish", "user_id", "subscription_id", "publish_date"),
        Index("ix_user_video_feed_user_nsfw_publish", "user_id", "is_nsfw", "publish_date"),
        Index("ix_user_video_feed_user_domain_publish_video", "user_id", "domain", "publish_date", "video_id"),
        Index("ix_user_video_feed_video_id", "video_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    publish_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    video_created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    domain: Mapped[str | None] = mapped_column(VARCHAR(255), nullable=True)
    is_nsfw: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
