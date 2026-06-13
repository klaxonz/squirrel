import logging

from infrastructure.scheduling.base import BaseTask, TaskRegistry
from domains.subscription.application.services.core.update.models import UpdateMode, UpdateTrigger
from domains.subscription.application.services.core.update.scheduler import scheduler

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=5, unit="minutes")
class SubscriptionIncrementalUpdateTask(BaseTask):
    """Subscription incremental update scheduled task
    Frequency: every 5 minutes
    Responsibility: Enqueue all active subscriptions for incremental update
    """

    @classmethod
    def run(cls):
        try:
            success, failed = scheduler.enqueue_due_states(
                trigger=UpdateTrigger.SCHEDULED,
                mode=UpdateMode.INCREMENTAL,
            )
            logger.info("Incremental due events emitted: success=%s, failed=%s", success, failed)
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("SubscriptionIncrementalUpdateTask.run error: %s", e, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionIncrementalUpdateTask task shutdown")

