from datetime import datetime

from sqlalchemy import Integer, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class SubscriptionVideo(Base, SerializerMixin):
    __tablename__ = "subscription_video"

    subscription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )


class VideoCreator(Base):
    __tablename__ = "video_creator"

    video_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    creator_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )


class UserSubscription(Base, SerializerMixin):
    __tablename__ = "user_subscription"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    is_enable: Mapped[bool] = mapped_column(Boolean, default=True)
    is_auto_download: Mapped[bool] = mapped_column(Boolean, default=False)
    is_download_all: Mapped[bool] = mapped_column(Boolean, default=False)
    is_extract_all: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )

    __table_args__ = (
        UniqueConstraint('user_id', 'subscription_id', name='uix_user_subscription'),
    )
