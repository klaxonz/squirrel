from dotenv import load_dotenv

load_dotenv(override=True)

import logging
from consumer.consumer_download_task import DownloadTaskConsumerThread
from consumer.consumer_extract_channel_video import ChannelVideoExtractAndDownloadConsumerThread
from consumer.consumer_subscribe_channel import SubscribeChannelConsumerThread

from model.message import Message
import uvicorn
from api.base import app
import common.constants as constants
from common.database import DatabaseManager
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from schedule.schedule import Scheduler, RetryFailedTask, AutoUpdateChannelVideoTask, RepairDownloadTaskInfo, \
    RepairChanelInfoForTotalVideos
from common.log import init_logging

logger = logging.getLogger(__name__)


def initialize_consumers():
    """启动所有消费者线程"""
    logger.info('Starting consumers...')
    download_consumers = []
    for _ in range(6):
        consumer = DownloadTaskConsumerThread(queue_name=constants.QUEUE_DOWNLOAD_TASK)
        download_consumers.append(consumer)
        consumer.start()

    channel_video_extract_consumers = []
    for _ in range(20):
        consumer = ChannelVideoExtractAndDownloadConsumerThread(queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD)
        channel_video_extract_consumers.append(consumer)
        consumer.start()

    # extract_info_consumer = ExtractorInfoTaskConsumerThread(queue_name=constants.QUEUE_EXTRACT_TASK)
    subscribe_consumer = SubscribeChannelConsumerThread(queue_name=constants.QUEUE_SUBSCRIBE_TASK)

    [consumer.start() for consumer in [
         subscribe_consumer
    ]]
    logger.info('Consumers started.')


def start_scheduler():
    """配置并启动定时任务调度器"""
    logger.info('Starting scheduler...')
    scheduler = Scheduler()
    scheduler.add_job(RepairDownloadTaskInfo.run, interval=60, unit='minutes')
    scheduler.add_job(RetryFailedTask.run, interval=1, unit='minutes')
    scheduler.add_job(AutoUpdateChannelVideoTask.run, interval=2, unit='minutes')
    scheduler.add_job(RepairChanelInfoForTotalVideos.run, interval=2, unit='minutes')
    scheduler.start()
    logger.info('Scheduler started.')


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
