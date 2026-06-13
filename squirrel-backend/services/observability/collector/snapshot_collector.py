from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import datetime

from services.observability.collector.keys import parse_metric_key
from services.observability.collector.snapshot import MetricSnapshot

logger = logging.getLogger(__name__)


class RedisMetricSnapshotCollector:
    def __init__(
        self,
        redis_client,
        get_metric_keys: Callable[[str], list[str]],
        get_histogram_stats: Callable[[str, dict[str, str] | None], dict[str, float]],
    ) -> None:
        self.redis = redis_client
        self._get_metric_keys = get_metric_keys
        self._get_histogram_stats = get_histogram_stats

    def collect(self, metric_names: list[str] | None = None) -> list[MetricSnapshot]:
        snapshots = []
        now = datetime.now()

        try:
            patterns = [f'metrics:*:{name}:*' for name in metric_names] if metric_names else ['metrics:*']
            for pattern in patterns:
                for key in self._get_metric_keys(pattern):
                    snapshot = self._build_snapshot(key, now)
                    if snapshot is not None:
                        snapshots.append(snapshot)
            return snapshots
        except (ConnectionError, OSError, TypeError, ValueError) as exc:
            logger.error('Failed to collect metric snapshots: %s', exc)
            return []

    def _build_snapshot(self, key: str, timestamp: datetime) -> MetricSnapshot | None:
        try:
            parsed_key = parse_metric_key(key)
            if parsed_key is None:
                return None

            metric_type, metric_name, labels = parsed_key
            value = self._read_metric_value(key, metric_type, metric_name, labels)
            if value is None:
                return None

            return MetricSnapshot(
                metric_name=metric_name,
                metric_type=metric_type,
                labels=labels,
                value=value,
                timestamp=timestamp,
            )
        except (ValueError, IndexError, TypeError, AttributeError) as exc:
            logger.debug('Failed to parse metric key %s: %s', key, exc)
            return None

    def _read_metric_value(
        self,
        key: str,
        metric_type: str,
        metric_name: str,
        labels: dict[str, str],
    ) -> float | None:
        if metric_type in {'counter', 'gauge'}:
            return float(self.redis.get(key) or 0)
        if metric_type == 'histogram':
            stats = self._get_histogram_stats(metric_name, labels)
            return stats.get('avg', 0)
        return None
