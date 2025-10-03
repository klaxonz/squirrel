from datetime import datetime
from typing import Optional

from sqlalchemy import Text, DateTime, Integer, VARCHAR, Index
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class Message(Base, SerializerMixin):
    __tablename__ = 'message'
    
    __table_args__ = (
        Index('ix_message_trace_id', 'trace_id'),
        Index('ix_message_queue_name', 'queue_name'),
        Index('ix_message_status', 'status'),
        Index('ix_message_created_at', 'created_at'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    trace_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    queue_name: Mapped[Optional[str]] = mapped_column(VARCHAR(128), nullable=True)
    message_type: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default='PENDING')
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    next_retry_time: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, default=None)
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(),
        onupdate=lambda: datetime.now()
    )
