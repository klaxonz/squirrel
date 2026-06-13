from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, TEXT, VARCHAR, DateTime, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from shared_kernel.domain.base import Base
from shared_kernel.domain.mixins import SerializerMixin


class SyncMode(StrEnum):
    INCREMENTAL = "incremental"
    FULL = "full"


class SyncStatus(StrEnum):
    IDLE = "idle"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class SubscriptionSyncState(Base, SerializerMixin):
    __tablename__ = "subscription_sync_state"

    __table_args__ = (
        UniqueConstraint("subscription_id", "sync_mode", name="uix_subscription_sync_state_sub_mode"),
        Index("ix_subscription_sync_state_subscription_id", "subscription_id"),
        Index("ix_subscription_sync_state_sync_status", "sync_status"),
        Index("ix_subscription_sync_state_next_sync_at", "next_sync_at"),
        Index("ix_subscription_sync_state_due_lookup", "sync_mode", "sync_status", "next_sync_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subscription_id: Mapped[int] = mapped_column(Integer, nullable=False)
    site: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    sync_mode: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default=SyncMode.INCREMENTAL.value)
    sync_status: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default=SyncStatus.IDLE.value)
    cursor_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)
    last_seen_video_url: Mapped[str | None] = mapped_column(VARCHAR(2048), nullable=True)
    last_head_sample_urls: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, default=list)
    last_head_fingerprint: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    last_known_total_available: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gap_suspicion_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gap_suspicion_reason: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    last_gap_detected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_full_requested_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    head_anchor_missing_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_sync_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    queued_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    queue_token: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    pending_video_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failure_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    idle_sync_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
