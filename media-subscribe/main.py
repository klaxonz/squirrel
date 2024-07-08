import threading

from dotenv import load_dotenv

load_dotenv(override=True)

import logging
from consumer.consumer_download_task import DownloadTaskConsumerThread
from consumer.consumer_extract_channel_video import ChannelVideoExtractConsumerThread, ChannelVideoExtractAndDownloadConsumerThread
from consumer.consumer_extract_video_info import ExtractorInfoTaskConsumerThread
from consumer.consumer_subscribe_channel import SubscribeChannelConsumerThread

from model.message import Message
import uvicorn
from api.base import app
import common.constants as constants
from common.database import DatabaseManager
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from schedule.schedule import Scheduler, RetryFailedTask, AutoUpdateChannelVideoTask
from common.log import init_logging

logger = logging.getLogger(__name__)


def initialize_consumers():
    """启动所有消费者线程"""
    logger.info('Starting consumers...')
    extract_info_consumer = ExtractorInfoTaskConsumerThread(queue_name=constants.QUEUE_EXTRACT_TASK)
    download_consumer = DownloadTaskConsumerThread(queue_name=constants.QUEUE_DOWNLOAD_TASK)
    subscribe_consumer = SubscribeChannelConsumerThread(queue_name=constants.QUEUE_SUBSCRIBE_TASK)
    channel_video_extract_consumer = ChannelVideoExtractConsumerThread(queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT)
    channel_video_extract_download_consumer = ChannelVideoExtractAndDownloadConsumerThread(queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD)
    [consumer.start() for consumer in [
        extract_info_consumer, download_consumer, subscribe_consumer, channel_video_extract_consumer,channel_video_extract_download_consumer
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
