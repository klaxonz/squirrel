"""Metrics collection scheduled task

Periodically collects metric snapshots from Redis, persists them to the database,
and cleans up expired data.
"""
import logging

from infrastructure.observability.metrics import metrics_service
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=5, unit="minutes")
class MetricsCollectionTask(BaseTask):
    """Metrics collection scheduled task

    Frequency: every 5 minutes
    Responsibilities:
    1. Collect metric snapshots from Redis
    2. Persist to PostgreSQL
    3. Provide data foundation for long-term analysis
    """

    @classmethod
    def run(cls):
        try:
            count = metrics_service.collect_and_persist()
            if count > 0:
                logger.info("Metrics collection completed: %s snapshots persisted", count)
            else:
                logger.debug("Metrics collection completed: no data to persist")
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("MetricsCollectionTask.run error: %s", e, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("MetricsCollectionTask task shutdown")


@TaskRegistry.register(interval=1, unit="days")
class MetricsCleanupTask(BaseTask):
    """Metrics cleanup scheduled task

    Frequency: once per day
    Responsibility: Clean up historical metric data beyond the retention period
    """

    @classmethod
    def run(cls):
        try:
            deleted = metrics_service.cleanup_old_metrics(days=30)
            if deleted > 0:
                logger.info("Metrics cleanup completed: %s old records deleted", deleted)
            else:
                logger.debug("Metrics cleanup completed: no old data to delete")
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("MetricsCleanupTask.run error: %s", e, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("MetricsCleanupTask task shutdown")
