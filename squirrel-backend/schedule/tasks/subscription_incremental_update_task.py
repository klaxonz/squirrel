import logging
from schedule.task import TaskRegistry, BaseTask
from services.subscription_update import scheduler
from services.subscription_update.models import UpdateTrigger, UpdateMode

logger = logging.getLogger()


@TaskRegistry.register(interval=5, unit='minutes')
class SubscriptionIncrementalUpdateTask(BaseTask):
    """
    订阅增量更新定时任务
    频率：每 5 分钟执行一次
    职责：将所有活跃订阅发送到增量更新队列
    """

    @classmethod
    def run(cls):
        try:
            success, failed = scheduler.enqueue_all_active(
                trigger=UpdateTrigger.SCHEDULED,
                mode=UpdateMode.INCREMENTAL
            )
            logger.info(f"Incremental update enqueued: success={success}, failed={failed}")
        except Exception as e:
            logger.error(f"SubscriptionIncrementalUpdateTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionIncrementalUpdateTask task shutdown")

