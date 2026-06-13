import logging

from scheduling.base import BaseTask, TaskRegistry
from services import subscription_service

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=3, unit="hours", start_immediately=False)
class SubscriptionAutoImportTask(BaseTask):
    """Auto-import unimported channels scheduled task
    Frequency: every 3 hours
    Responsibility: Auto-import channels not yet imported for all users across sites
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
            logger.error("SubscriptionAutoImportTask.run error: %s", e, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionAutoImportTask task shutdown")
