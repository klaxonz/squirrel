from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, Index, Integer, UniqueConstraint, VARCHAR
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class SubscriptionSyncTrendProjection(Base, SerializerMixin):
    __tablename__ = 'subscription_sync_trend_projection'

    __table_args__ = (
        UniqueConstraint(
            'bucket_time',
            'bucket_granularity',
            'site',
            'sync_mode',
            'trigger',
            name='uix_subscription_sync_trend_bucket_dims',
        ),
        Index('ix_subscription_sync_trend_bucket_time', 'bucket_time'),
        Index('ix_subscription_sync_trend_site_bucket', 'site', 'bucket_time'),
        Index('ix_subscription_sync_trend_dims_bucket', 'site', 'sync_mode', 'trigger', 'bucket_time'),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    bucket_granularity: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default='hour')
    site: Mapped[str] = mapped_column(VARCHAR(64), nullable=False, default='')
    sync_mode: Mapped[str] = mapped_column(VARCHAR(16), nullable=False, default='')
    trigger: Mapped[str] = mapped_column(VARCHAR(32), nullable=False, default='')
    runs_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runs_success: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runs_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runs_deferred: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_found: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_enqueued: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_extracted: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    videos_skipped: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_total_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    avg_duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    p95_duration_ms: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
