import json
import logging
from typing import Dict, Any

from common import constants
from core.database import get_session
from crawl import DownloaderFactory
from models.task.download_task import DownloadTask
from models.message import Message
from models.task.task_state import TaskState
from services import video_service, subscription_video_service, task_service
from services import subscription_service
from mq import mq_consumer

logger = logging.getLogger()


@mq_consumer(constants.QUEUE_VIDEO_DOWNLOAD, group="download", consumer_name="download")
def process_download_message(message: Dict[str, Any]):
    _process_download_message_unified(message)


@mq_consumer(constants.QUEUE_VIDEO_DOWNLOAD_SCHEDULED, group="download", consumer_name="download-scheduled")
def process_download_scheduled_message(message: Dict[str, Any]):
    _process_download_message_unified(message)


def _process_download_message_unified(message: Dict[str, Any]):
    try:
        logger.info(f"开始处理下载任务: {message}")

        message_obj = Message.from_dict(message)
        video, download_task, subscription = _prepare_download_task(message_obj)

        downloader = DownloaderFactory.create_downloader(video.url)
        task_state = downloader.download(subscription, video, download_task, "video_download")

        task_service.update_task_status(download_task.id, task_state)

        logger.info(f"视频下载完成: {video.title}, URL: {video.url}")

    except Exception as e:
        logger.error(f"处理下载任务时发生错误: {e}", exc_info=True)
        raise


def _prepare_download_task(message):
    with get_session() as session:
        download_task = DownloadTask.from_dict(json.loads(message.body))
        download_task = task_service.get_task_by_id(download_task.id)
        download_task = session.merge(download_task)
        video = video_service.get_video_by_id(download_task.video_id)
        subscription_video = subscription_video_service.get_subscription_video_by_video_id(video.id)
        subscription = subscription_service.get_subscription_by_id(subscription_video.subscription_id)
        download_task.transition_to(TaskState.DOWNLOADING.value)
        session.commit()
        return video, download_task, subscription
