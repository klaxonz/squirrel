import logging

from services import subscription_sync_state_service

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
            video_result = subscription_sync_state_service.reconcile_pending_video_counts()
            drained_result = subscription_sync_state_service.reconcile_terminal_drained_sync_states()
            queued_result = subscription_sync_state_service.recover_stale_queued_sync_states()
            running_result = subscription_sync_state_service.recover_stale_running_sync_states()
            retry_wait_result = subscription_sync_state_service.reconcile_retry_wait_run_projections()
            logger.info(
                "Subscription pending reconcile completed: video_states=%s videos=%s drained_completed=%s drained_failed=%s queued_recovered=%s running_recovered=%s retry_wait_repaired=%s",
                video_result["states"],
                video_result["videos"],
                drained_result["completed"],
                drained_result["failed"],
                queued_result["recovered"],
                running_result["recovered"],
                retry_wait_result["repaired"],
            )
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error("SubscriptionPendingReconcileTask.run error: %s", e, exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionPendingReconcileTask task shutdown")
