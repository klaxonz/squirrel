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
            result = subscription_sync_state_service.reconcile_pending_video_counts()
            logger.info(
                "Subscription pending reconcile completed: states=%s, videos=%s",
                result["states"],
                result["videos"],
            )
        except Exception as e:
            logger.error(f"SubscriptionPendingReconcileTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionPendingReconcileTask task shutdown")
