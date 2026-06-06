"""
指标收集定时任务

定期从 Redis 收集指标快照并持久化到数据库，同时清理过期数据。
"""
import logging
from schedule.task import TaskRegistry, BaseTask
from services.metrics_service import metrics_service

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=5, unit='minutes')
class MetricsCollectionTask(BaseTask):
    """
    指标收集定时任务
    
    频率：每 5 分钟执行一次
    职责：
    1. 从 Redis 收集指标快照
    2. 持久化到 PostgreSQL
    3. 为长期分析提供数据基础
    """

    @classmethod
    def run(cls):
        try:
            count = metrics_service.collect_and_persist()
            if count > 0:
                logger.info(f"Metrics collection completed: {count} snapshots persisted")
            else:
                logger.debug("Metrics collection completed: no data to persist")
        except Exception as e:
            logger.error(f"MetricsCollectionTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("MetricsCollectionTask task shutdown")


@TaskRegistry.register(interval=1, unit='days')
class MetricsCleanupTask(BaseTask):
    """
    指标清理定时任务
    
    频率：每天执行一次
    职责：清理超过保留期限的历史指标数据
    """

    @classmethod
    def run(cls):
        try:
            deleted = metrics_service.cleanup_old_metrics(days=30)
            if deleted > 0:
                logger.info(f"Metrics cleanup completed: {deleted} old records deleted")
            else:
                logger.debug("Metrics cleanup completed: no old data to delete")
        except Exception as e:
            logger.error(f"MetricsCleanupTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("MetricsCleanupTask task shutdown")
