from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, Boolean, JSON, VARCHAR, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from models import Base


class Video(Base):
    __tablename__ = "video"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
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
