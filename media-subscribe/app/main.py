from dotenv import load_dotenv

from common.config import GlobalConfig

load_dotenv(override=True)

import logging
from consumer.consumer_download_task import DownloadTaskConsumerThread
from consumer.consumer_extract import ChannelVideoExtractAndDownloadConsumerThread
from consumer.consumer_subscribe_channel import SubscribeChannelConsumerThread

from model.message import Message
import uvicorn
from api.base import app
import common.constants as constants
from common.database import DatabaseManager
from model.channel import Channel, ChannelVideo
from model.download_task import DownloadTask
from schedule.schedule import Scheduler, AutoUpdateChannelVideoTask, SyncCookies, RepairChanelInfoForTotalVideos, \
    RetryFailedTask, RepairDownloadTaskInfo, ChangeStatusTask, RepairChannelVideoDuration
from common.log import init_logging

logger = logging.getLogger(__name__)


def start_consumers():
    """启动所有消费者线程"""
    logger.info('Starting consumers...')
    download_consumers = []
    for idx in range(5):
        consumer = DownloadTaskConsumerThread(queue_name=constants.QUEUE_DOWNLOAD_TASK, thread_id=idx)
        download_consumers.append(consumer)
        consumer.start()

    channel_video_extract_consumers = []
    for idx in range(10):
        consumer = ChannelVideoExtractAndDownloadConsumerThread(
            queue_name=constants.QUEUE_CHANNEL_VIDEO_EXTRACT_DOWNLOAD, thread_id=idx)
        channel_video_extract_consumers.append(consumer)
        consumer.start()

    subscribe_consumer = SubscribeChannelConsumerThread(queue_name=constants.QUEUE_SUBSCRIBE_TASK, thread_id=1)
    subscribe_consumer.start()

    logger.info('Consumers started.')


def start_scheduler():
    """配置并启动定时任务调度器"""
    logger.info('Starting scheduler...')
    scheduler = Scheduler()
    if GlobalConfig.get_cookie_type() == 'cookiecloud':
        SyncCookies.run()
        scheduler.add_job(SyncCookies.run, interval=60, unit='minutes', start_immediately=False)
    scheduler.add_job(ChangeStatusTask.run, interval=1, unit='minutes')
    scheduler.add_job(RepairDownloadTaskInfo.run, interval=60, unit='minutes')
    scheduler.add_job(RetryFailedTask.run, interval=1, unit='minutes')
    scheduler.add_job(AutoUpdateChannelVideoTask.run, interval=10, unit='minutes')
    scheduler.add_job(RepairChanelInfoForTotalVideos.run, interval=2, unit='minutes')
    scheduler.add_job(RepairChannelVideoDuration.run, interval=120, unit='minutes')
    scheduler.start()
    logger.info('Scheduler started.')


if __name__ == "__main__":
    # 初始化日志配置
    init_logging()
    # 初始化数据库
    tables = [DownloadTask, Channel, ChannelVideo, Message]
    DatabaseManager.initialize_database(tables)

    start_scheduler()
    start_consumers()

    # 启动服务
    logger.info('Starting server...')
    uvicorn.run(app, host="0.0.0.0", port=8000)
