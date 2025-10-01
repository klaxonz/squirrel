import logging
from schedule.task import TaskRegistry, BaseTask
from services.subscription_update import scheduler

logger = logging.getLogger()


@TaskRegistry.register(interval=300, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    """
    定时调度所有订阅更新任务
    职责：触发订阅更新调度器，具体更新逻辑由调度器和编排器处理
    """

    @classmethod
    def run(cls):
        try:
            success, failed = scheduler.schedule_all_active(batch_size=100)
            logger.info(f"Auto update completed: success={success}, failed={failed}")
        except Exception as e:
            logger.error(f"AutoUpdateChannelVideo.run error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        logger.info("AutoUpdateChannelVideo task shutdown")
