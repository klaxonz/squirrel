import threading

from dotenv import load_dotenv

load_dotenv(override=True)

import logging
from consumer.consumer_download_task import DownloadTaskConsumerThread
from consumer.consumer_extract_channel_video import ExtractorChannelVideoConsumerThread
from consumer.consumer_extract_video_info import ExtractorInfoTaskConsumerThread
from consumer.consumer_subscribe_channel import SubscribeChannelConsumerThread

from model.message import Message
import uvicorn
from api.base import app
from common.constants import QUEUE_DOWNLOAD_TASK, QUEUE_SUBSCRIBE_TASK, QUEUE_EXTRACT_TASK, QUEUE_CHANNEL_VIDEO_UPDATE
from common.database import DatabaseManager
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from schedule.schedule import Scheduler, RetryFailedTask, AutoUpdateChannelVideoTask
from common.log import init_logging

logger = logging.getLogger(__name__)


def initialize_consumers():
    """启动所有消费者线程"""
    logger.info('Starting consumers...')
    extract_info_consumer = ExtractorInfoTaskConsumerThread(queue_name=QUEUE_EXTRACT_TASK)
    download_consumer = DownloadTaskConsumerThread(queue_name=QUEUE_DOWNLOAD_TASK)
    subscribe_consumer = SubscribeChannelConsumerThread(queue_name=QUEUE_SUBSCRIBE_TASK)
    subscribe_channel_video_consumer = ExtractorChannelVideoConsumerThread(queue_name=QUEUE_CHANNEL_VIDEO_UPDATE)
    [consumer.start() for consumer in [
        extract_info_consumer, download_consumer, subscribe_consumer, subscribe_channel_video_consumer
    ]]
    logger.info('Consumers started.')


def _start_scheduler():
    """配置并启动定时任务调度器"""
    logger.info('Starting scheduler...')
    scheduler = Scheduler()
    scheduler.add_job(RetryFailedTask.run, interval=1, unit='minutes')
    scheduler.add_job(AutoUpdateChannelVideoTask.run, interval=2, unit='minutes')
    logger.info('Scheduler started.')


def start_scheduler():
    scheduler_thread = threading.Thread(target=_start_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()


if __name__ == "__main__":
    # 初始化日志配置
    init_logging()
    # 初始化数据库
    tables = [DownloadTask, Channel, ChannelVideo, Message]
    DatabaseManager.initialize_database(tables)

    initialize_consumers()
    start_scheduler()

    # 启动服务
    logger.info('Starting server...')
    uvicorn.run(app, host="0.0.0.0", port=8000)
