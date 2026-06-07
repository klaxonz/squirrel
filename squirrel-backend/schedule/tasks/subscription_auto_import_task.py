import logging

from schedule.task import BaseTask, TaskRegistry
from services import subscription_service

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=3, unit="hours", start_immediately=False)
class SubscriptionAutoImportTask(BaseTask):
    """自动导入未导入频道定时任务
    频率：每 3 小时执行一次
    职责：为所有用户自动导入各站点尚未导入的频道
    """

    @classmethod
    def run(cls):
        try:
            result = subscription_service.auto_import_missing_subscriptions()
            logger.info(
                "Subscription auto import completed: users=%s sites=%s imported=%s skipped=%s failed=%s",
                result.get("users"),
                result.get("sites"),
                result.get("imported"),
                result.get("skipped"),
                result.get("failed"),
            )
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error(f"SubscriptionAutoImportTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionAutoImportTask task shutdown")
