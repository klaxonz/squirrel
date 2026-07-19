import logging

from domains.subscription.application.services.core.update.models import UpdateMode, UpdateTrigger
from domains.subscription.application.services.core.update.scheduler import scheduler
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=60 * 2, unit='minutes')
class SubscriptionFullUpdateTask(BaseTask):
    """Subscription full update scheduled task
    Frequency: every 60 minutes (1 hour)
    Responsibility: Enqueue all active subscriptions for full update
    """

    @classmethod
    def run(cls):
        success, failed = scheduler.enqueue_due_states(
            trigger=UpdateTrigger.SCHEDULED,
            mode=UpdateMode.FULL,
        )
        logger.info('Full due events emitted: success=%s, failed=%s', success, failed)
        if failed:
            raise RuntimeError(f'Failed to enqueue {failed} full subscription syncs')
