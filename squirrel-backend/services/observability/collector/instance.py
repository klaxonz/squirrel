import logging

from services.observability.collector.redis_collector import MetricsCollector

logger = logging.getLogger(__name__)
_metrics_instance: MetricsCollector | None = None


def get_metrics_collector() -> MetricsCollector:
    """Get the global metrics collector instance."""
    global _metrics_instance

    if _metrics_instance is None:
        from core.cache import redis_client

        _metrics_instance = MetricsCollector(redis_client)
        logger.info('Metrics collector initialized')

    return _metrics_instance


metrics = get_metrics_collector()
