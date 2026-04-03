import logging

from schedule.task import TaskRegistry, BaseTask
from services import subscription_sync_state_service

logger = logging.getLogger()


@TaskRegistry.register(interval=10, unit='minutes')
class SubscriptionPendingReconcileTask(BaseTask):
    """
    对账订阅待处理视频计数
    频率：每 10 分钟执行一次
    职责：扫描视频提取队列并回写 subscription_sync_state.pending_video_count
    """

    @classmethod
    def run(cls):
        try:
            video_result = subscription_sync_state_service.reconcile_pending_video_counts()
            drained_result = subscription_sync_state_service.reconcile_terminal_drained_sync_states()
            queued_result = subscription_sync_state_service.recover_stale_queued_sync_states()
            running_result = subscription_sync_state_service.recover_stale_running_sync_states()
            logger.info(
                "Subscription pending reconcile completed: video_states=%s videos=%s drained_completed=%s drained_failed=%s queued_recovered=%s running_recovered=%s",
                video_result["states"],
                video_result["videos"],
                drained_result["completed"],
                drained_result["failed"],
                queued_result["recovered"],
                running_result["recovered"],
            )
        except Exception as e:
            logger.error(f"SubscriptionPendingReconcileTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionPendingReconcileTask task shutdown")
