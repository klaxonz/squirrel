from datetime import datetime

from sqlalchemy import Integer, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class VideoHistory(Base, SerializerMixin):
    __tablename__ = "video_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    video_id: Mapped[int] = mapped_column(Integer, nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    end_time: Mapped[datetime] = mapped_column(DateTime)
    duration: Mapped[float] = mapped_column(Float)
    watch_duration: Mapped[int] = mapped_column(Integer, default=0)
    last_position: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
