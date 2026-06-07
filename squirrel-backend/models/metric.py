"""Metric snapshot data model

Used to persist metric data from Redis for long-term querying and analysis.
"""
from datetime import datetime

from sqlalchemy import DECIMAL, VARCHAR, DateTime, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class MetricSnapshot(Base, SerializerMixin):
    """Metric snapshot table

    Stores metric data collected from Redis for historical analysis and trend queries.

    Features:
    - Time range query support
    - Filter by metric name and labels
    - Automatic cleanup of expired data (30-day retention)
    """

    __tablename__ = "metric_snapshot"

    __table_args__ = (
        # Primary query index: metric name and time
        Index("ix_metric_name_timestamp", "metric_name", "timestamp"),
        # Label query index (JSONB GIN index, PostgreSQL only)
        Index("ix_metric_labels", "labels", postgresql_using="gin"),
        # Type filter index
        Index("ix_metric_type", "metric_type"),
        # Time range query optimization
        Index("ix_metric_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # Metric name, e.g. "crawl.tasks.total"
    metric_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)

    # Metric type: counter, gauge, histogram
    metric_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)

    # Labels (JSONB format), e.g. {"site": "youtube", "status": "success"}
    # Uses JSONB instead of JSON for GIN index support and better query performance
    labels: Mapped[dict | None] = mapped_column(JSONB, default={})

    # Metric value
    value: Mapped[float] = mapped_column(DECIMAL(20, 6), nullable=False)

    # Snapshot timestamp
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # Creation time
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(),
        nullable=False,
    )
