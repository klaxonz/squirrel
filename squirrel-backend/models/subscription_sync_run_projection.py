from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class SubscriptionSyncRunProjection(Base, SerializerMixin):
    __tablename__ = 'subscription_sync_run_projection'

    __table_args__ = (
        Index('ix_subscription_sync_run_projection_subscription', 'subscription_id'),
        Index('ix_subscription_sync_run_projection_status_time', 'status', 'last_event_at'),
        Index('ix_subscription_sync_run_projection_site_time', 'site', 'last_event_at'),
        Index('ix_subscription_sync_run_projection_started_at', 'started_at'),
        Index('ix_subscription_sync_run_projection_finished_at', 'finished_at'),
        Index('ix_subscription_sync_run_projection_subscription_time', 'subscription_id', 'last_event_at'),
        Index('ix_subscription_sync_run_projection_subscription_started', 'subscription_id', 'started_at'),
    )

    run_id: Mapped[str] = mapped_column(VARCHAR(64), primary_key=True)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sync_state_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    site: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    sync_mode: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    trigger: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default='created')
    current_phase: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    queued_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_type: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(VARCHAR(1024), nullable=True)
    videos_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_enqueued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    pending_video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_seq_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_event_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
