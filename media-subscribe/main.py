from alembic.config import Config
from dotenv import load_dotenv

from alembic import command
from common.config import GlobalConfig

load_dotenv(override=True)

import logging
from consumer.consumer_download_task import DownloadTaskConsumerThread
from consumer.consumer_extract import ChannelVideoExtractAndDownloadConsumerThread
from consumer.consumer_subscribe_channel import SubscribeChannelConsumerThread
import uvicorn
from schedule.schedule import (
    Scheduler
)
from common.log import init_logging
from common import constants
from schedule import TaskRegistry


def create_app():
    from api.base import app
    return app


logger = logging.getLogger(__name__)

download_consumers = []
channel_video_extract_consumers = []
subscribe_consumer = None


def upgrade_database():
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

def start_consumers():
    """启动所有消费者线程"""
    logger.info('Starting consumers...')
    global download_consumers, channel_video_extract_consumers, subscribe_consumer

    # Stop existing consumers
    for consumer in download_consumers + channel_video_extract_consumers:
        consumer.stop()
    if subscribe_consumer:
        subscribe_consumer.stop()

    download_consumers = []
    for idx in range(GlobalConfig.DOWNLOAD_CONSUMERS):
        consumer = DownloadTaskConsumerThread(queue_name=constants.QUEUE_DOWNLOAD_TASK, thread_id=idx)
        download_consumers.append(consumer)
        consumer.start()

    channel_video_extract_consumers = []
    for idx in range(GlobalConfig.EXTRACT_CONSUMERS):
        consumer = ChannelVideoExtractAndDownloadConsumerThread(
            queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD, thread_id=idx)
        channel_video_extract_consumers.append(consumer)
        consumer.start()

    subscribe_consumer = SubscribeChannelConsumerThread(queue_name=constants.QUEUE_SUBSCRIBE_TASK, thread_id=0)
    subscribe_consumer.start()

    logger.info('Consumers started.')


def start_scheduler():
    """配置并启动定时任务调度器"""
    logger.info('Starting scheduler...')
    scheduler = Scheduler()
    
    for task_class in TaskRegistry.tasks:
        logger.info(f"Registering task: {task_class.__name__} with interval {task_class.interval} {task_class.unit}")
        scheduler.add_job(
            task_class.run,
            interval=task_class.interval,
            unit=task_class.unit,
            start_immediately=task_class.start_immediately
        )
    
    scheduler.start()
    logger.info('Scheduler started.')


def restart_consumers():
    global download_consumers, channel_video_extract_consumers, subscribe_consumer

    # Stop existing consumers
    for consumer in download_consumers + channel_video_extract_consumers:
        consumer.stop()
    if subscribe_consumer:
        subscribe_consumer.stop()

    # Clear existing consumers
    download_consumers.clear()
    channel_video_extract_consumers.clear()
    subscribe_consumer = None

    # Start new consumers
    start_consumers()


def start_fastapi_server():
    app = create_app()
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    # 初始化日志配置
    init_logging()
    # 初始化数据库
    upgrade_database()

    start_scheduler()
    start_consumers()

    # 启动服务
    logger.info('Starting server...')
    start_fastapi_server()
