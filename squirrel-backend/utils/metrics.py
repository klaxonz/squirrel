"""轻量级指标收集器

基于 Redis 实现的可观测性指标系统，无需额外中间件。

核心功能：
- Counter: 计数器（累加）
- Gauge: 瞬时值（最新值）
- Histogram: 分布统计（P50/P95/P99）
- Timer: 计时器上下文管理器

存储策略：
- 实时数据存储在 Redis（1小时 TTL）
- 定期快照写入 PostgreSQL（长期存储）
- 支持按标签（tags）聚合和查询

示例：
    from utils.metrics import metrics

    # 计数器
    metrics.counter("crawl.tasks.total", tags={"site": "youtube", "status": "success"})

    # 瞬时值
    metrics.gauge("queue.depth", 42, tags={"queue": "video_extract"})

    # 分布统计
    metrics.histogram("crawl.duration", 2.5, tags={"site": "youtube"})

    # 计时器
    with metrics.timer("video.extract", tags={"site": "youtube"}):
        extract_video()
"""

import logging
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MetricSnapshot:
    """指标快照数据类"""

    metric_name: str
    metric_type: str  # counter, gauge, histogram
    labels: dict[str, str]
    value: float
    timestamp: datetime

    def to_dict(self) -> dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        return {
            "metric_name": self.metric_name,
            "metric_type": self.metric_type,
            "labels": self.labels,
            "value": self.value,
            "timestamp": self.timestamp.isoformat(),
        }


class MetricsCollector:
    """轻量级指标收集器

    特性：
    - 基于 Redis 实现，无需额外中间件
    - 支持标签（tags）多维度聚合
    - 自动时间窗口聚合（1分钟粒度）
    - 低开销，适合高频调用
    """

    def __init__(self, redis_client):
        """初始化指标收集器

        Args:
            redis_client: Redis 客户端实例

        """
        self.redis = redis_client
        self.ttl = 3600  # 1小时 TTL
        self.enabled = True  # 可通过配置动态开关

    def counter(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        """计数器：累加型指标

        用于：请求次数、任务数、错误数等

        Args:
            name: 指标名称，如 "crawl.tasks.total"
            value: 增量值，默认 1
            tags: 标签字典，如 {"site": "youtube", "status": "success"}

        示例：
            metrics.counter("crawl.tasks.total", tags={"site": "youtube", "status": "success"})

        """
        if not self.enabled:
            return

        try:
            key = self._build_key(name, tags, metric_type="counter", window="1m")
            self.redis.incrby(key, value)
            self.redis.expire(key, self.ttl)

            # 同时更新总计（无时间窗口）
            total_key = self._build_key(name, tags, metric_type="counter", window="total")
            self.redis.incrby(total_key, value)
            self.redis.expire(total_key, self.ttl * 24)  # 24小时

        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to record counter metric {name}: {e}")

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """瞬时值：记录当前状态

        用于：队列深度、活跃连接数、CPU使用率等

        Args:
            name: 指标名称，如 "queue.depth"
            value: 当前值
            tags: 标签字典

        示例：
            metrics.gauge("queue.depth", 42, tags={"queue": "video_extract"})

        """
        if not self.enabled:
            return

        try:
            key = self._build_key(name, tags, metric_type="gauge")
            self.redis.set(key, value, ex=self.ttl)
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to record gauge metric {name}: {e}")

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """分布统计：记录数值分布，支持百分位数查询

        用于：请求延迟、处理时长、数据大小等

        实现：使用 Sorted Set 存储，score 为时间戳，支持自动过期

        Args:
            name: 指标名称，如 "crawl.duration"
            value: 数值
            tags: 标签字典

        示例：
            metrics.histogram("crawl.duration", 2.5, tags={"site": "youtube"})

        """
        if not self.enabled:
            return

        try:
            key = self._build_key(name, tags, metric_type="histogram", window="1m")
            timestamp = time.time()

            # 使用 Sorted Set: member 格式为 "timestamp:value"，score 为 timestamp
            member = f"{timestamp}:{value}"
            self.redis.zadd(key, {member: timestamp})
            self.redis.expire(key, self.ttl)

            # 清理旧数据（超过1分钟的）
            cutoff = timestamp - 60
            self.redis.zremrangebyscore(key, 0, cutoff)

        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to record histogram metric {name}: {e}")

    def record_error(self, site: str, url: str, error_type: str, error_msg: str, max_records: int = 100) -> None:
        """记录错误详情到 Redis List，用于问题排查

        Args:
            site: 站点名称
            url: 出错的 URL
            error_type: 错误类型
            error_msg: 错误消息（可包含堆栈）
            max_records: 最多保留的记录数

        """
        if not self.enabled:
            return

        try:
            import json
            from datetime import datetime

            key = "metrics:errors:recent"
            record = json.dumps(
                {
                    "time": datetime.now().isoformat(),
                    "site": site,
                    "url": url,
                    "type": error_type,
                    "msg": error_msg[:2000],  # 保留更多内容以包含堆栈
                }
            )

            # LPUSH + LTRIM 保持最新的 N 条记录
            self.redis.lpush(key, record)
            self.redis.ltrim(key, 0, max_records - 1)
            self.redis.expire(key, 86400)  # 24小时过期

        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to record error detail: {e}")

    def get_recent_errors(self, limit: int = 50) -> list:
        """获取最近的错误记录"""
        try:
            import json

            key = "metrics:errors:recent"
            records = self.redis.lrange(key, 0, limit - 1)
            return [json.loads(r) for r in records]
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to get recent errors: {e}")
            return []

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None):
        """计时器上下文管理器：自动记录代码块执行时间

        用于：函数执行时长、操作耗时等

        Args:
            name: 指标名称
            tags: 标签字典

        示例：
            with metrics.timer("video.extract", tags={"site": "youtube"}):
                extract_video()

        """
        start_time = time.time()
        exception_occurred = False

        try:
            yield
        except Exception:
            exception_occurred = True
            raise
        finally:
            duration = time.time() - start_time

            # 记录耗时分布
            self.histogram(f"{name}.duration", duration, tags=tags)

            # 记录状态计数
            status_tags = {**(tags or {}), "status": "error" if exception_occurred else "success"}
            self.counter(f"{name}.total", tags=status_tags)

    def _build_key(
        self,
        name: str,
        tags: dict[str, str] | None,
        metric_type: str,
        window: str = "",
    ) -> str:
        """构建 Redis key

        格式：metrics:{metric_type}:{name}:{tag1=val1,tag2=val2}:{window}:{minute}

        Args:
            name: 指标名称
            tags: 标签字典
            metric_type: 指标类型
            window: 时间窗口（如 "1m", "total"）

        Returns:
            Redis key 字符串

        """
        parts = ["metrics", metric_type, name]

        # 添加标签（排序保证一致性）
        if tags:
            tag_str = ",".join(f"{k}={v}" for k, v in sorted(tags.items()))
            parts.append(tag_str)
        else:
            parts.append("_")

        # 添加时间窗口
        if window:
            if window == "total":
                parts.append("total")
            else:
                # 按分钟分桶
                minute = datetime.now().strftime("%Y%m%d%H%M")
                parts.append(f"{window}:{minute}")

        return ":".join(parts)

    def get_counter(self, name: str, tags: dict[str, str] | None = None, window: str = "1m") -> int:
        """查询计数器值

        Args:
            name: 指标名称
            tags: 标签字典
            window: 时间窗口（"1m" 或 "total"）

        Returns:
            计数值

        """
        try:
            key = self._build_key(name, tags, metric_type="counter", window=window)
            value = self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to get counter metric {name}: {e}")
            return 0

    def get_gauge(self, name: str, tags: dict[str, str] | None = None) -> float | None:
        """查询瞬时值

        Args:
            name: 指标名称
            tags: 标签字典

        Returns:
            当前值，如果不存在返回 None

        """
        try:
            key = self._build_key(name, tags, metric_type="gauge")
            value = self.redis.get(key)
            return float(value) if value else None
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to get gauge metric {name}: {e}")
            return None

    def get_histogram_stats(
        self,
        name: str,
        tags: dict[str, str] | None = None,
    ) -> dict[str, float]:
        """查询分布统计（P50, P95, P99, avg, min, max, count）

        Args:
            name: 指标名称
            tags: 标签字典

        Returns:
            统计字典，包含百分位数和基本统计量

        """
        try:
            key = self._build_key(name, tags, metric_type="histogram", window="1m")

            # 获取所有数据点
            members = self.redis.zrange(key, 0, -1)
            if not members:
                return {
                    "count": 0,
                    "min": 0,
                    "max": 0,
                    "avg": 0,
                    "p50": 0,
                    "p95": 0,
                    "p99": 0,
                }

            # 解析数值（member 格式为 "timestamp:value"）
            values = []
            for member in members:
                if isinstance(member, bytes):
                    member = member.decode("utf-8")
                try:
                    _, value_str = member.split(":", 1)
                    values.append(float(value_str))
                except (ValueError, IndexError):
                    continue

            if not values:
                return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

            values.sort()
            count = len(values)

            return {
                "count": count,
                "min": values[0],
                "max": values[-1],
                "avg": sum(values) / count,
                "p50": self._percentile(values, 0.50),
                "p95": self._percentile(values, 0.95),
                "p99": self._percentile(values, 0.99),
            }

        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to get histogram stats for {name}: {e}")
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

    def _percentile(self, sorted_values: list[float], percentile: float) -> float:
        """计算百分位数

        Args:
            sorted_values: 已排序的数值列表
            percentile: 百分位数（0-1）

        Returns:
            百分位数值

        """
        if not sorted_values:
            return 0.0

        k = (len(sorted_values) - 1) * percentile
        f = int(k)
        c = f + 1

        if c >= len(sorted_values):
            return sorted_values[-1]

        d0 = sorted_values[f] * (c - k)
        d1 = sorted_values[c] * (k - f)
        return d0 + d1

    def get_metrics_keys_by_pattern(self, pattern: str) -> list[str]:
        """根据模式查询指标 key

        Args:
            pattern: Redis key 模式，如 "metrics:counter:crawl.tasks.total:*"

        Returns:
            匹配的 key 列表

        """
        try:
            return [k.decode("utf-8") if isinstance(k, bytes) else k for k in self.redis.keys(pattern)]
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error(f"Failed to get metrics keys by pattern {pattern}: {e}")
            return []

    def collect_snapshots(self, metric_names: list[str] | None = None) -> list[MetricSnapshot]:
        """收集指标快照（用于持久化到数据库）

        Args:
            metric_names: 要收集的指标名称列表，None 表示收集所有

        Returns:
            指标快照列表

        """
        snapshots = []
        now = datetime.now()

        try:
            # 扫描所有指标 key
            if metric_names:
                patterns = [f"metrics:*:{name}:*" for name in metric_names]
            else:
                patterns = ["metrics:*"]

            for pattern in patterns:
                keys = self.get_metrics_keys_by_pattern(pattern)

                for key in keys:
                    try:
                        # 解析 key: metrics:{type}:{name}:{tags}:{window}:{time}
                        parts = key.split(":")
                        if len(parts) < 4:
                            continue

                        metric_type = parts[1]
                        metric_name = parts[2]
                        tags_str = parts[3]

                        # 解析标签
                        labels = {}
                        if tags_str != "_":
                            for tag in tags_str.split(","):
                                if "=" in tag:
                                    k, v = tag.split("=", 1)
                                    labels[k] = v

                        # 获取值
                        value = None
                        if metric_type == "counter" or metric_type == "gauge":
                            value = float(self.redis.get(key) or 0)
                        elif metric_type == "histogram":
                            stats = self.get_histogram_stats(metric_name, labels)
                            value = stats.get("avg", 0)

                        if value is not None:
                            snapshot = MetricSnapshot(
                                metric_name=metric_name,
                                metric_type=metric_type,
                                labels=labels,
                                value=value,
                                timestamp=now,
                            )
                            snapshots.append(snapshot)

                    except (ValueError, IndexError, TypeError, AttributeError) as e:
                        logger.debug(f"Failed to parse metric key {key}: {e}")
                        continue

            return snapshots

        except (ConnectionError, OSError, TypeError, ValueError) as e:
            logger.error(f"Failed to collect metric snapshots: {e}")
            return []

    def enable(self) -> None:
        """启用指标收集"""
        self.enabled = True
        logger.info("Metrics collection enabled")

    def disable(self) -> None:
        """禁用指标收集（用于调试或降低开销）"""
        self.enabled = False
        logger.info("Metrics collection disabled")


# 全局实例（延迟初始化）
_metrics_instance: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器实例

    Returns:
        MetricsCollector 实例

    """
    global _metrics_instance

    if _metrics_instance is None:
        from core.cache import redis_client

        _metrics_instance = MetricsCollector(redis_client)
        logger.info("Metrics collector initialized")

    return _metrics_instance


# 便捷访问
metrics = get_metrics_collector()
