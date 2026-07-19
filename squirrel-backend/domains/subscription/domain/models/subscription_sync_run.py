from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, TEXT, VARCHAR, DateTime, ForeignKey, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from infrastructure.database.base import Base


class SyncRunStatus(StrEnum):
    QUEUED = 'queued'
    RUNNING = 'running'
    WAITING_VIDEOS = 'waiting_videos'
    SUCCEEDED = 'succeeded'
    FAILED = 'failed'
    DEFERRED = 'deferred'
    CANCELLED = 'cancelled'


class SubscriptionSyncRun(Base):
    """Durable execution ledger for one logical subscription sync.

    A full sync may span multiple crawl tasks, but all of those tasks share one run row.
    ``SubscriptionSyncState.current_run_id`` is the fencing pointer that decides which run
    may mutate the state projection.
    """

    __tablename__ = 'subscription_sync_run'

    __table_args__ = (
        Index('ix_subscription_sync_run_state_status', 'sync_state_id', 'status'),
        Index('ix_subscription_sync_run_subscription_created', 'subscription_id', 'created_at'),
        Index('ix_subscription_sync_run_status_updated', 'status', 'updated_at'),
        Index('ix_subscription_sync_run_trace_id', 'trace_id'),
    )

    id: Mapped[str] = mapped_column(VARCHAR(64), primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            'subscription.id',
            name='fk_subscription_sync_run_subscription_id_subscription',
            ondelete='CASCADE',
        ),
        nullable=False,
    )
    sync_state_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey(
            'subscription_sync_state.id',
            name='fk_subscription_sync_run_sync_state_id_sync_state',
            ondelete='SET NULL',
        ),
        nullable=True,
    )
    site: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default='')
    sync_mode: Mapped[str] = mapped_column(VARCHAR(16), nullable=False)
    trigger: Mapped[str | None] = mapped_column(VARCHAR(32), nullable=True)
    status: Mapped[str] = mapped_column(VARCHAR(24), nullable=False, default=SyncRunStatus.QUEUED.value)
    queue_token: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    request_id: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    trace_id: Mapped[str | None] = mapped_column(VARCHAR(64), nullable=True)
    cursor_in: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    cursor_out: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    videos_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_enqueued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(TEXT, nullable=True)
    last_error_type: Mapped[str | None] = mapped_column(VARCHAR(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
