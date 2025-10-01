import logging
from schedule.task import TaskRegistry, BaseTask
from services.subscription_update import scheduler

logger = logging.getLogger()


@TaskRegistry.register(interval=300, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    """
    定时调度所有订阅更新任务
    职责：将所有活跃订阅发送到消息队列，按 domain 并行处理
    """

    @classmethod
    def run(cls):
        try:
            success, failed = scheduler.enqueue_all_active()
            logger.info(f"Auto update enqueued: success={success}, failed={failed}")
        except Exception as e:
            logger.error(f"AutoUpdateChannelVideo.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("AutoUpdateChannelVideo task shutdown")
