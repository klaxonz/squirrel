from datetime import datetime

from sqlalchemy import VARCHAR, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class BlockedVideoRecord(Base, SerializerMixin):
    __tablename__ = "blocked_video_record"

    __table_args__ = (
        Index("ix_blocked_video_url", "url"),
        Index("ix_blocked_video_site", "site"),
        Index("ix_blocked_video_reason_code", "reason_code"),
        Index("ix_blocked_video_created_at", "created_at"),
        Index("ux_blocked_video_url_unique", "url", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(VARCHAR(2048), nullable=False)
    site: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    reason_code: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_type: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(default=lambda: datetime.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
