from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Index, Integer, JSON, Text, UniqueConstraint, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class SubscriptionSyncEvent(Base, SerializerMixin):
    __tablename__ = 'subscription_sync_event'

    __table_args__ = (
        UniqueConstraint('stream_id', 'seq_no', name='uix_subscription_sync_event_stream_seq'),
        Index('ix_subscription_sync_event_stream_id', 'stream_id'),
        Index('ix_subscription_sync_event_subscription_time', 'subscription_id', 'occurred_at'),
        Index('ix_subscription_sync_event_site_time', 'site', 'occurred_at'),
        Index('ix_subscription_sync_event_type_time', 'event_type', 'occurred_at'),
        Index('ix_subscription_sync_event_run_lookup', 'subscription_id', 'sync_state_id', 'occurred_at'),
        Index('ix_subscription_sync_event_request_id', 'request_id'),
        Index('ix_subscription_sync_event_trace_id', 'trace_id'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    stream_id: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    sync_state_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    site: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    sync_mode: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    trigger: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    request_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    trace_id: Mapped[Optional[str]] = mapped_column(VARCHAR(64), nullable=True)
    event_type: Mapped[str] = mapped_column(VARCHAR(64), nullable=False)
    event_phase: Mapped[Optional[str]] = mapped_column(VARCHAR(32), nullable=True)
    event_status: Mapped[Optional[str]] = mapped_column(VARCHAR(16), nullable=True)
    seq_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=dict)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
