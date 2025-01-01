from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy.orm import Mapped, mapped_column

from models import Base


class SubscriptionVideo(Base):
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

