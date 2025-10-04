"""
进度记录模型
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import Integer, BigInteger, Text, Numeric, Index
from sqlalchemy.dialects.mysql import VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class ProgressRecord(Base, SerializerMixin):
    """
    进度记录表
    用于持久化爬取进度，便于查询和统计
    """
    __tablename__ = 'progress_record'
    
    __table_args__ = (
        Index('ix_progress_trace_id', 'trace_id'),
        Index('ix_progress_subscription_id', 'subscription_id'),
        Index('ix_progress_event_type', 'event_type'),
        Index('ix_progress_created_at', 'created_at'),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    trace_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    subscription_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    video_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    url: Mapped[Optional[str]] = mapped_column(VARCHAR(2048), nullable=True)
    
    current_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    progress_percentage: Mapped[float] = mapped_column(Numeric(5, 2), default=0.0)
    
    message: Mapped[Optional[str]] = mapped_column(VARCHAR(512), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now()
    )

