"""Metrics service

Responsible for metrics data persistence, querying and aggregation analysis.
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func

from core.database import get_session
from models.metric import MetricSnapshot as MetricSnapshotModel
from utils.metrics import MetricSnapshot, metrics

logger = logging.getLogger(__name__)


class MetricsService:
    """Metrics service

    Features:
    - Periodically collect metric snapshots from Redis and persist to database
    - Provide metric query and aggregation API
    - Manage historical data (auto-clean expired data)
    """

    def __init__(self):
        self.retention_days = 30  # 30-day data retention

    def persist_snapshots(self, snapshots: list[MetricSnapshot]) -> int:
        """Persist metric snapshots to database

        Args:
            snapshots: List of metric snapshots

        Returns:
            Number of successfully written records

        """
        if not snapshots:
            return 0

        try:
            with get_session() as db:
                records = []
                for snapshot in snapshots:
                    record = MetricSnapshotModel(
                        metric_name=snapshot.metric_name,
                        metric_type=snapshot.metric_type,
                        labels=snapshot.labels,
                        value=snapshot.value,
                        timestamp=snapshot.timestamp,
                        created_at=datetime.now(),
                    )
                    records.append(record)

                db.bulk_save_objects(records)

                logger.info("Persisted %s metric snapshots to database", len(records))
                return len(records)

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to persist metric snapshots: %s", e)
            return 0

    def collect_and_persist(self, metric_names: list[str] | None = None) -> int:
        """Collect metric snapshots from Redis and persist

        Args:
            metric_names: List of metric names to collect, None means collect all

        Returns:
            Number of successfully written records

        """
        try:
            snapshots = metrics.collect_snapshots(metric_names)
            return self.persist_snapshots(snapshots)
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to collect and persist metrics: %s", e)
            return 0

    def get_metric_timeseries(
        self,
        metric_name: str,
        labels: dict[str, str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        interval_minutes: int = 5,
    ) -> list[dict[str, Any]]:
        """Query metric time-series data

        Args:
            metric_name: Metric name
            labels: Label filter conditions
            start_time: Start time (default 1 hour ago)
            end_time: End time (default current time)
            interval_minutes: Aggregation interval in minutes

        Returns:
            Time-series data list, format: [{"timestamp": "2025-12-07T20:00:00", "value": 123}, ...]

        """
        try:
            with get_session() as db:
                # 默认时间范围：最近1小时
                if not end_time:
                    end_time = datetime.now()
                if not start_time:
                    start_time = end_time - timedelta(hours=1)

                # 构建查询
                query = db.query(
                    func.date_trunc("minute", MetricSnapshotModel.timestamp).label("time_bucket"),
                    func.avg(MetricSnapshotModel.value).label("avg_value"),
                    func.min(MetricSnapshotModel.value).label("min_value"),
                    func.max(MetricSnapshotModel.value).label("max_value"),
                    func.count(MetricSnapshotModel.id).label("count"),
                ).filter(
                    and_(
                        MetricSnapshotModel.metric_name == metric_name,
                        MetricSnapshotModel.timestamp >= start_time,
                        MetricSnapshotModel.timestamp <= end_time,
                    ),
                )

                # 添加标签过滤
                if labels:
                    for key, value in labels.items():
                        query = query.filter(
                            MetricSnapshotModel.labels[key].astext == value,
                        )

                # 按时间分组
                query = query.group_by("time_bucket").order_by("time_bucket")

                results = query.all()

                return [
                    {
                        "timestamp": row.time_bucket.isoformat(),
                        "value": float(row.avg_value),
                        "min": float(row.min_value),
                        "max": float(row.max_value),
                        "count": row.count,
                    }
                    for row in results
                ]

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to query metric timeseries for %s: %s", metric_name, e)
            return []

    def get_metric_aggregation(
        self,
        metric_name: str,
        labels: dict[str, str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, float]:
        """Query metric aggregation statistics

        Args:
            metric_name: Metric name
            labels: Label filter conditions
            start_time: Start time
            end_time: End time

        Returns:
            Aggregation statistics including count, min, max, avg, sum

        """
        try:
            with get_session() as db:
                # 默认时间范围：最近1小时
                if not end_time:
                    end_time = datetime.now()
                if not start_time:
                    start_time = end_time - timedelta(hours=1)

                # 构建查询
                query = db.query(
                    func.count(MetricSnapshotModel.id).label("count"),
                    func.min(MetricSnapshotModel.value).label("min_value"),
                    func.max(MetricSnapshotModel.value).label("max_value"),
                    func.avg(MetricSnapshotModel.value).label("avg_value"),
                    func.sum(MetricSnapshotModel.value).label("sum_value"),
                ).filter(
                    and_(
                        MetricSnapshotModel.metric_name == metric_name,
                        MetricSnapshotModel.timestamp >= start_time,
                        MetricSnapshotModel.timestamp <= end_time,
                    ),
                )

                # 添加标签过滤
                if labels:
                    for key, value in labels.items():
                        query = query.filter(
                            MetricSnapshotModel.labels[key].astext == value,
                        )

                result = query.first()

                if not result or result.count == 0:
                    return {
                        "count": 0,
                        "min": 0,
                        "max": 0,
                        "avg": 0,
                        "sum": 0,
                    }

                return {
                    "count": result.count,
                    "min": float(result.min_value) if result.min_value else 0,
                    "max": float(result.max_value) if result.max_value else 0,
                    "avg": float(result.avg_value) if result.avg_value else 0,
                    "sum": float(result.sum_value) if result.sum_value else 0,
                }

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to query metric aggregation for %s: %s", metric_name, e)
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0}

    def get_metrics_by_labels(
        self,
        label_key: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """Query metrics grouped by label (e.g. crawl stats per site)

        Args:
            label_key: Label key name, e.g. "site"
            start_time: Start time
            end_time: End time

        Returns:
            Statistics list grouped by label

        """
        try:
            with get_session() as db:
                # 默认时间范围：最近1小时
                if not end_time:
                    end_time = datetime.now()
                if not start_time:
                    start_time = end_time - timedelta(hours=1)

                # 查询所有记录
                results = db.query(MetricSnapshotModel).filter(
                    and_(
                        MetricSnapshotModel.timestamp >= start_time,
                        MetricSnapshotModel.timestamp <= end_time,
                        MetricSnapshotModel.labels.isnot(None),
                    ),
                ).all()

                # 手动分组聚合（因为 JSON 字段分组在 SQLAlchemy 中较复杂）
                groups = {}
                for record in results:
                    label_value = record.labels.get(label_key) if record.labels else None
                    if not label_value:
                        continue

                    key = f"{record.metric_name}:{label_value}"
                    if key not in groups:
                        groups[key] = {
                            "metric_name": record.metric_name,
                            "label_key": label_key,
                            "label_value": label_value,
                            "count": 0,
                            "sum": 0,
                            "avg": 0,
                            "min": float("inf"),
                            "max": float("-inf"),
                        }

                    groups[key]["count"] += 1
                    groups[key]["sum"] += float(record.value)
                    groups[key]["min"] = min(groups[key]["min"], float(record.value))
                    groups[key]["max"] = max(groups[key]["max"], float(record.value))

                # 计算平均值
                for group in groups.values():
                    if group["count"] > 0:
                        group["avg"] = group["sum"] / group["count"]

                return list(groups.values())

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to query metrics by labels: %s", e)
            return []

    def cleanup_old_metrics(self, days: int | None = None) -> int:
        """Clean up expired metric data

        Args:
            days: Retention days, defaults to retention_days

        Returns:
            Number of deleted records

        """
        try:
            with get_session() as db:
                retention_days = days or self.retention_days
                cutoff_date = datetime.now() - timedelta(days=retention_days)

                deleted_count = db.query(MetricSnapshotModel).filter(
                    MetricSnapshotModel.timestamp < cutoff_date,
                ).delete()

                logger.info("Cleaned up %s old metric records (older than %s days)", deleted_count, retention_days)
                return deleted_count

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error("Failed to cleanup old metrics: %s", e)
            return 0


# 全局实例
metrics_service = MetricsService()
