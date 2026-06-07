"""指标快照数据模型

用于持久化存储 Redis 中的指标数据，支持长期查询和分析。
"""
from datetime import datetime

from sqlalchemy import DECIMAL, VARCHAR, DateTime, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from models import Base
from models.mixins.serializer import SerializerMixin


class MetricSnapshot(Base, SerializerMixin):
    """指标快照表

    存储从 Redis 收集的指标数据，用于历史分析和趋势查询。

    特性：
    - 支持按时间范围查询
    - 支持按指标名称和标签过滤
    - 自动清理过期数据（保留30天）
    """

    __tablename__ = "metric_snapshot"

    __table_args__ = (
        # 主查询索引：按指标名称和时间查询
        Index("ix_metric_name_timestamp", "metric_name", "timestamp"),
        # 标签查询索引（JSONB GIN 索引，PostgreSQL 专用）
        Index("ix_metric_labels", "labels", postgresql_using="gin"),
        # 类型过滤索引
        Index("ix_metric_type", "metric_type"),
        # 时间范围查询优化
        Index("ix_metric_timestamp", "timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # 指标名称，如 "crawl.tasks.total"
    metric_name: Mapped[str] = mapped_column(VARCHAR(128), nullable=False)

    # 指标类型：counter, gauge, histogram
    metric_type: Mapped[str] = mapped_column(VARCHAR(32), nullable=False)

    # 标签（JSONB 格式），如 {"site": "youtube", "status": "success"}
    # 使用 JSONB 而不是 JSON，支持 GIN 索引和更好的查询性能
    labels: Mapped[dict | None] = mapped_column(JSONB, default={})

    # 指标值
    value: Mapped[float] = mapped_column(DECIMAL(20, 6), nullable=False)

    # 快照时间戳
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)

    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(),
        nullable=False,
    )
