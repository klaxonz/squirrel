import logging

from domains.subscription.application.services.core.sync.lifecycle import subscription_sync_lifecycle
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=10, unit="minutes")
class SubscriptionPendingReconcileTask(BaseTask):
    """Reconcile subscription pending video counts
    Frequency: every 10 minutes
    Responsibility: Scan the video extraction queue and write back subscription_sync_state.pending_video_count
    """

    @classmethod
    def run(cls):
        try:
            result = subscription_sync_lifecycle.recover()
            logger.info(
                "Subscription pending reconcile completed: video_states=%s videos=%s drained_completed=%s drained_failed=%s queued_recovered=%s running_recovered=%s",
                result.video_states,
                result.videos,
                result.drained_completed,
                result.drained_failed,
                result.queued_recovered,
                result.running_recovered,
            )
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("SubscriptionPendingReconcileTask.run error: %s", e, exc_info=True)
