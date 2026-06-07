"""指标服务

负责指标数据的持久化、查询和聚合分析。
"""
import logging
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import and_, func

from core.database import get_db
from models.metric import MetricSnapshot as MetricSnapshotModel
from utils.metrics import MetricSnapshot, metrics

logger = logging.getLogger(__name__)


class MetricsService:
    """指标服务

    功能：
    - 定期从 Redis 收集指标快照并持久化到数据库
    - 提供指标查询和聚合 API
    - 管理历史数据（自动清理过期数据）
    """

    def __init__(self):
        self.retention_days = 30  # 保留30天数据

    def persist_snapshots(self, snapshots: list[MetricSnapshot]) -> int:
        """持久化指标快照到数据库

        Args:
            snapshots: 指标快照列表

        Returns:
            成功写入的记录数

        """
        if not snapshots:
            return 0

        db = next(get_db())
        try:
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
            db.commit()

            logger.info(f"Persisted {len(records)} metric snapshots to database")
            return len(records)

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            db.rollback()
            logger.error(f"Failed to persist metric snapshots: {e}")
            return 0
        finally:
            db.close()

    def collect_and_persist(self, metric_names: list[str] | None = None) -> int:
        """从 Redis 收集指标快照并持久化

        Args:
            metric_names: 要收集的指标名称列表，None 表示收集所有

        Returns:
            成功写入的记录数

        """
        try:
            snapshots = metrics.collect_snapshots(metric_names)
            return self.persist_snapshots(snapshots)
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error(f"Failed to collect and persist metrics: {e}")
            return 0

    def get_metric_timeseries(
        self,
        metric_name: str,
        labels: dict[str, str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        interval_minutes: int = 5,
    ) -> list[dict[str, Any]]:
        """查询指标时间序列数据

        Args:
            metric_name: 指标名称
            labels: 标签过滤条件
            start_time: 开始时间（默认1小时前）
            end_time: 结束时间（默认当前时间）
            interval_minutes: 聚合间隔（分钟）

        Returns:
            时间序列数据列表，格式：[{"timestamp": "2025-12-07T20:00:00", "value": 123}, ...]

        """
        db = next(get_db())
        try:
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
            logger.error(f"Failed to query metric timeseries for {metric_name}: {e}")
            return []
        finally:
            db.close()

    def get_metric_aggregation(
        self,
        metric_name: str,
        labels: dict[str, str] | None = None,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> dict[str, float]:
        """查询指标聚合统计

        Args:
            metric_name: 指标名称
            labels: 标签过滤条件
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            聚合统计，包含 count, min, max, avg, sum

        """
        db = next(get_db())
        try:
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
            logger.error(f"Failed to query metric aggregation for {metric_name}: {e}")
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "sum": 0}
        finally:
            db.close()

    def get_metrics_by_labels(
        self,
        label_key: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[dict[str, Any]]:
        """按标签分组查询指标（如：各站点的爬取统计）

        Args:
            label_key: 标签键名，如 "site"
            start_time: 开始时间
            end_time: 结束时间

        Returns:
            按标签分组的统计列表

        """
        db = next(get_db())
        try:
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
            logger.error(f"Failed to query metrics by labels: {e}")
            return []
        finally:
            db.close()

    def cleanup_old_metrics(self, days: int | None = None) -> int:
        """清理过期的指标数据

        Args:
            days: 保留天数，默认使用 retention_days

        Returns:
            删除的记录数

        """
        db = next(get_db())
        try:
            retention_days = days or self.retention_days
            cutoff_date = datetime.now() - timedelta(days=retention_days)

            deleted_count = db.query(MetricSnapshotModel).filter(
                MetricSnapshotModel.timestamp < cutoff_date,
            ).delete()

            db.commit()

            logger.info(f"Cleaned up {deleted_count} old metric records (older than {retention_days} days)")
            return deleted_count

        except (ConnectionError, OSError, ValueError, TypeError) as e:
            db.rollback()
            logger.error(f"Failed to cleanup old metrics: {e}")
            return 0
        finally:
            db.close()


# 全局实例
metrics_service = MetricsService()
