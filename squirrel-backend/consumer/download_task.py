import json
import logging

import dramatiq
from sqlalchemy import select

from common import constants
from core.database import get_session
from downloader.downloader import Downloader
from models.download_task import DownloadTask
from models.message import Message
from services import video_service, subscription_video_service
from services import subscription_service

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_DOWNLOAD)
def process_download_message(message):
    _process_download_message(message, constants.QUEUE_VIDEO_DOWNLOAD)


@dramatiq.actor(queue_name=constants.QUEUE_VIDEO_DOWNLOAD_SCHEDULED)
def process_download_scheduled_message(message):
    _process_download_message(message, constants.QUEUE_VIDEO_DOWNLOAD_SCHEDULED)


def _process_download_message(message, queue: str):
    try:
        logger.info(f"开始处理下载任务: {message}")
        message_obj = Message.from_dict(message)
        video, download_task, subscription = _prepare_download_task(message_obj)
        status = Downloader.download(subscription, video, download_task, queue)
        _update_task_status(download_task, status)

        logger.info(f"download video finished, video title: {video.title}, video url: {video.url}")
    except Exception as e:
        logger.error(f"处理下载任务时发生错误: {e}", exc_info=True)


def _prepare_download_task(message):
    with get_session() as session:
        download_task = DownloadTask.from_dict(json.loads(message.body))
        download_task = session.merge(download_task)
        video = video_service.get_video_by_id(download_task.video_id)
        subscription_video = subscription_video_service.get_subscription_video_by_video_id(video.id)
        subscription = subscription_service.get_subscription_by_id(subscription_video.subscription_id)
        logger.info(f"start download video, video title: {video.title}, video url: {video.url}")
        download_task.status = 'DOWNLOADING'
        session.commit()
        return video, download_task, subscription


def _update_task_status(download_task, status):
    with get_session() as session:
        download_task = session.merge(download_task)
        if status == 0:
            download_task.status = 'COMPLETED'
            download_task.error_message = ''
        elif status == 1:
            download_task.status = 'FAILED'
        elif status == 2:
            download_task.status = 'PAUSED'
        session.commit()
