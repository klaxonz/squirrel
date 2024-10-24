import logging
from datetime import datetime

import dramatiq

from common import constants
from core.cache import RedisClient
from core.database import get_session
from downloader.downloader import Downloader
from model.channel import ChannelVideo
from model.download_task import DownloadTask
from model.message import Message

logger = logging.getLogger(__name__)


# 在文件末尾添加
__all__ = ['process_download_message']


@dramatiq.actor(queue_name=constants.QUEUE_DOWNLOAD_TASK)
def process_download_message(message: str):
    try:
        logger.info(f"开始处理下载任务: {message}")
        message_obj = Message.model_validate(message)
        download_task = _prepare_download_task(message_obj)
        status = _download_video(download_task, constants.QUEUE_DOWNLOAD_TASK)
        _update_task_status(download_task, status)
        logger.info(f"下载视频结束, channel: {download_task.channel_name}, video: {download_task.url}")
    except Exception as e:
        logger.error(f"处理下载任务时发生错误: {e}", exc_info=True)


def _prepare_download_task(message):
    with get_session() as session:
        download_task = DownloadTask.model_validate(message.body)
        logger.info(f"下载视频开始, channel: {download_task.channel_name}, video: {download_task.url}")
        download_task.status = 'DOWNLOADING'
        session.commit()
        session.expunge(download_task)
    return download_task


def _download_video(download_task, task_name):
    return Downloader.download(download_task.task_id, download_task.url, task_name)


def _update_task_status(download_task, status):
    with get_session() as session:
        download_task = session.query(DownloadTask).filter(
            DownloadTask.task_id == download_task.task_id).one()

        if status == 0:
            _handle_completed_download(download_task, session)
        elif status == 1:
            download_task.status = 'FAILED'
        elif status == 2:
            download_task.status = 'PAUSED'

        session.commit()


def _handle_completed_download(download_task, session):
    download_task.status = 'COMPLETED'
    download_task.error_message = ''
    session.commit()

    channel_video = session.query(ChannelVideo).filter(
        ChannelVideo.video_id == download_task.video_id).first()
    if channel_video:
        channel_video.if_downloaded = True
        session.commit()

    _update_redis_cache(download_task)


def _update_redis_cache(download_task):
    key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{download_task.domain}:{download_task.video_id}"
    RedisClient.get_instance().client.hset(key, 'if_download', datetime.now().timestamp())

