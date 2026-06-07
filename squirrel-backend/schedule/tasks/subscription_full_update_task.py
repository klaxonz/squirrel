import logging

from schedule.task import BaseTask, TaskRegistry
from services.subscription_update import scheduler
from services.subscription_update.models import UpdateMode, UpdateTrigger

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=60 * 2, unit="minutes")
class SubscriptionFullUpdateTask(BaseTask):
    """Subscription full update scheduled task
    Frequency: every 60 minutes (1 hour)
    Responsibility: Enqueue all active subscriptions for full update
    """

    @classmethod
    def run(cls):
        try:
            success, failed = scheduler.enqueue_due_states(
                trigger=UpdateTrigger.SCHEDULED,
                mode=UpdateMode.FULL,
            )
            logger.info("Full due events emitted: success=%s, failed=%s", success, failed)
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("SubscriptionFullUpdateTask.run error: %s", e, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionFullUpdateTask task shutdown")

