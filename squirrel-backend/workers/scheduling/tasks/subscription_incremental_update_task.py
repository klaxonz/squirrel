import logging

from domains.subscription.application.services.core.update.models import UpdateMode, UpdateTrigger
from domains.subscription.application.services.core.update.scheduler import scheduler
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=5, unit='minutes')
class SubscriptionIncrementalUpdateTask(BaseTask):
    """Subscription incremental update scheduled task
    Frequency: every 5 minutes
    Responsibility: Enqueue all active subscriptions for incremental update
    """

    @classmethod
    def run(cls):
        success, failed = scheduler.enqueue_due_states(
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.INCREMENTAL,
        )
        logger.info('Incremental due events emitted: success=%s, failed=%s', success, failed)
        if failed:
            raise RuntimeError(f'Failed to enqueue {failed} incremental subscription syncs')
