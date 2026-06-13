from datetime import datetime

from sqlalchemy import VARCHAR, DateTime, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.base import Base
from shared_kernel.domain.mixins import SerializerMixin


class Message(Base, SerializerMixin):
    __tablename__ = "message"

    __table_args__ = (
        Index("ix_message_trace_id", "trace_id"),
        Index("ix_message_queue_name", "queue_name"),
        Index("ix_message_status", "status"),
        Index("ix_message_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    queue_name: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    message_type: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default="PENDING")
    error_msg: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_time: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now(),
    )
