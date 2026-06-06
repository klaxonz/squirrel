import logging
from schedule.task import TaskRegistry, BaseTask
from services.subscription_update import scheduler
from services.subscription_update.models import UpdateTrigger, UpdateMode

logger = logging.getLogger(__name__)


@TaskRegistry.register(interval=60 * 2, unit='minutes')
class SubscriptionFullUpdateTask(BaseTask):
    """
    订阅全量更新定时任务
    频率：每 60 分钟（1 小时）执行一次
    职责：将所有活跃订阅发送到全量更新队列
    """

    @classmethod
    def run(cls):
        try:
            success, failed = scheduler.enqueue_due_states(
                trigger=UpdateTrigger.SCHEDULED,
                mode=UpdateMode.FULL
            )
            logger.info(f"Full due events emitted: success={success}, failed={failed}")
        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.error(f"SubscriptionFullUpdateTask.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("SubscriptionFullUpdateTask task shutdown")

