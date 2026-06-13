"""Lightweight metrics collector

Redis-based observability metrics system, no additional middleware required.

Core features:
- Counter: cumulative counter
- Gauge: instantaneous value
- Histogram: distribution statistics (P50/P95/P99)
- Timer: timer context manager

Storage strategy:
- Real-time data stored in Redis (1-hour TTL)
- Periodic snapshots written to PostgreSQL (long-term storage)
- Supports tag-based aggregation and querying

Example:
    from services.observability.collector.instance import metrics

    # Counter
    metrics.counter("crawl.tasks.total", tags={"site": "youtube", "status": "success"})

    # Gauge
    metrics.gauge("queue.depth", 42, tags={"queue": "video_extract"})

    # Histogram
    metrics.histogram("crawl.duration", 2.5, tags={"site": "youtube"})

    # Timer
    with metrics.timer("video.extract", tags={"site": "youtube"}):
        extract_video()
"""

import logging
import time
from contextlib import contextmanager

from services.observability.collector.keys import build_metric_key
from services.observability.collector.recent_errors import RecentErrorStore
from services.observability.collector.snapshot import MetricSnapshot
from services.observability.collector.snapshot_collector import RedisMetricSnapshotCollector

logger = logging.getLogger(__name__)


class MetricsCollector:
    """Lightweight metrics collector

    Features:
    - Redis-based, no additional middleware required
    - Multi-dimensional tag aggregation
    - Automatic time window aggregation (1-minute granularity)
    - Low overhead, suitable for high-frequency use
    """

    def __init__(self, redis_client):
        """Initialize the metrics collector

        Args:
            redis_client: Redis client instance

        """
        self.redis = redis_client
        self.ttl = 3600  # 1-hour TTL
        self.enabled = True  # Can be toggled via config
        self.recent_errors = RecentErrorStore(redis_client)
        self.snapshot_collector = RedisMetricSnapshotCollector(
            redis_client,
            self.get_metrics_keys_by_pattern,
            self.get_histogram_stats,
        )

    def counter(self, name: str, value: int = 1, tags: dict[str, str] | None = None) -> None:
        """Counter: cumulative metric

        Used for: request count, task count, error count, etc.

        Args:
            name: Metric name, e.g. "crawl.tasks.total"
            value: Increment value, default 1
            tags: Tag dict, e.g. {"site": "youtube", "status": "success"}

        Example:
            metrics.counter("crawl.tasks.total", tags={"site": "youtube", "status": "success"})

        """
        if not self.enabled:
            return

        try:
            key = self._build_key(name, tags, metric_type="counter", window="1m")
            self.redis.incrby(key, value)
            self.redis.expire(key, self.ttl)

            # Also update the total (no time window)
            total_key = self._build_key(name, tags, metric_type="counter", window="total")
            self.redis.incrby(total_key, value)
            self.redis.expire(total_key, self.ttl * 24)  # 24 hours

        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to record counter metric %s: %s", name, e)

    def gauge(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Gauge: records current state

        Used for: queue depth, active connections, CPU usage, etc.

        Args:
            name: Metric name, e.g. "queue.depth"
            value: Current value
            tags: Tag dict

        Example:
            metrics.gauge("queue.depth", 42, tags={"queue": "video_extract"})

        """
        if not self.enabled:
            return

        try:
            key = self._build_key(name, tags, metric_type="gauge")
            self.redis.set(key, value, ex=self.ttl)
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to record gauge metric %s: %s", name, e)

    def histogram(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Histogram: records value distribution with percentile support

        Used for: request latency, processing time, data size, etc.

        Implementation: Uses Sorted Set with timestamp as score, supports auto-expiry

        Args:
            name: Metric name, e.g. "crawl.duration"
            value: Value
            tags: Tag dict

        Example:
            metrics.histogram("crawl.duration", 2.5, tags={"site": "youtube"})

        """
        if not self.enabled:
            return

        try:
            key = self._build_key(name, tags, metric_type="histogram", window="1m")
            timestamp = time.time()

            # Use Sorted Set: member format is "timestamp:value", score is timestamp
            member = f"{timestamp}:{value}"
            self.redis.zadd(key, {member: timestamp})
            self.redis.expire(key, self.ttl)

            # Clean up old data (older than 1 minute)
            cutoff = timestamp - 60
            self.redis.zremrangebyscore(key, 0, cutoff)

        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to record histogram metric %s: %s", name, e)

    def record_error(self, site: str, url: str, error_type: str, error_msg: str, max_records: int = 100) -> None:
        """Record error details to Redis List for troubleshooting

        Args:
            site: Site name
            url: URL that caused the error
            error_type: Error type
            error_msg: Error message (may include stack trace)
            max_records: Maximum number of records to keep

        """
        if not self.enabled:
            return

        try:
            self.recent_errors.record(site, url, error_type, error_msg, max_records=max_records)
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to record error detail: %s", e)

    def get_recent_errors(self, limit: int = 50) -> list:
        """Get recent error records"""
        try:
            return self.recent_errors.list_recent(limit)
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to get recent errors: %s", e)
            return []

    @contextmanager
    def timer(self, name: str, tags: dict[str, str] | None = None):
        """Timer context manager: automatically records code block execution time

        Used for: function execution duration, operation latency, etc.

        Args:
            name: Metric name
            tags: Tag dict

        Example:
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

            # Record duration distribution
            self.histogram(f"{name}.duration", duration, tags=tags)

            # Record status count
            status_tags = {**(tags or {}), "status": "error" if exception_occurred else "success"}
            self.counter(f"{name}.total", tags=status_tags)

    def _build_key(
        self,
        name: str,
        tags: dict[str, str] | None,
        metric_type: str,
        window: str = "",
    ) -> str:
        """Build a Redis key

        Format: metrics:{metric_type}:{name}:{tag1=val1,tag2=val2}:{window}:{minute}

        Args:
            name: Metric name
            tags: Tag dict
            metric_type: Metric type
            window: Time window (e.g. "1m", "total")

        Returns:
            Redis key string

        """
        return build_metric_key(name, tags, metric_type, window)

    def get_counter(self, name: str, tags: dict[str, str] | None = None, window: str = "1m") -> int:
        """Query counter value

        Args:
            name: Metric name
            tags: Tag dict
            window: Time window ("1m" or "total")

        Returns:
            Counter value

        """
        try:
            key = self._build_key(name, tags, metric_type="counter", window=window)
            value = self.redis.get(key)
            return int(value) if value else 0
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to get counter metric %s: %s", name, e)
            return 0

    def get_gauge(self, name: str, tags: dict[str, str] | None = None) -> float | None:
        """Query gauge value

        Args:
            name: Metric name
            tags: Tag dict

        Returns:
            Current value, or None if not present

        """
        try:
            key = self._build_key(name, tags, metric_type="gauge")
            value = self.redis.get(key)
            return float(value) if value else None
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to get gauge metric %s: %s", name, e)
            return None

    def get_histogram_stats(
        self,
        name: str,
        tags: dict[str, str] | None = None,
    ) -> dict[str, float]:
        """Query histogram statistics (P50, P95, P99, avg, min, max, count)

        Args:
            name: Metric name
            tags: Tag dict

        Returns:
            Statistics dict containing percentiles and basic statistics

        """
        try:
            key = self._build_key(name, tags, metric_type="histogram", window="1m")

            # Get all data points
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

            # Parse values (member format is "timestamp:value")
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
            logger.error("Failed to get histogram stats for %s: %s", name, e)
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}

    def _percentile(self, sorted_values: list[float], percentile: float) -> float:
        """Calculate percentile

        Args:
            sorted_values: Sorted list of values
            percentile: Percentile (0-1)

        Returns:
            Percentile value

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
        """Query metric keys by pattern

        Args:
            pattern: Redis key pattern, e.g. "metrics:counter:crawl.tasks.total:*"

        Returns:
            List of matching keys

        """
        try:
            return [k.decode("utf-8") if isinstance(k, bytes) else k for k in self.redis.keys(pattern)]
        except Exception as e:
            # infrastructure boundary -- metrics must never crash the caller
            logger.error("Failed to get metrics keys by pattern %s: %s", pattern, e)
            return []

    def collect_snapshots(self, metric_names: list[str] | None = None) -> list[MetricSnapshot]:
        """Collect metric snapshots (for persistence to database)

        Args:
            metric_names: List of metric names to collect, None means collect all

        Returns:
            List of metric snapshots

        """
        return self.snapshot_collector.collect(metric_names)

    def enable(self) -> None:
        """Enable metrics collection"""
        self.enabled = True
        logger.info("Metrics collection enabled")

    def disable(self) -> None:
        """Disable metrics collection (for debugging or reducing overhead)"""
        self.enabled = False
        logger.info("Metrics collection disabled")

