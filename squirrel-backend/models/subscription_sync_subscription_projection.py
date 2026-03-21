from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class SubscriptionSyncSubscriptionProjection(Base, SerializerMixin):
    __tablename__ = 'subscription_sync_subscription_projection'

    __table_args__ = (
        Index('ix_subscription_sync_subscription_projection_status', 'current_status'),
        Index('ix_subscription_sync_subscription_projection_next_sync', 'next_sync_at'),
        Index('ix_subscription_sync_subscription_projection_updated_at', 'updated_at'),
        Index(
            'ix_subscription_sync_subscription_projection_status_next_sync',
            'current_status',
            'next_sync_at',
        ),
    )

    subscription_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    latest_run_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    current_status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default='idle')
    current_phase: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    next_sync_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    last_error_message: Mapped[Optional[str]] = mapped_column(VARCHAR(1024), nullable=True)
    pending_video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
