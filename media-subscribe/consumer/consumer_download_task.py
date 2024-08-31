import json
import logging
from datetime import datetime

from common import constants
from common.cache import RedisClient
from common.database import get_session
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.channel import ChannelVideo
from model.download_task import DownloadTaskSchema, DownloadTask
from model.message import MessageSchema

logger = logging.getLogger(__name__)


class DownloadTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            message = None
            task_id = None

            try:
                message = self._dequeue_message()
                if message:
                    download_task = self._process_message(message)
                    status = self._download_video(download_task)
                    self._update_task_status(download_task, status)
                    logger.info(f"下载视频结束, channel: {download_task.channel_name}, video: {download_task.url}")
            except Exception as e:
                self._handle_error(e, message, task_id)

    def _dequeue_message(self):
        with get_session() as session:
            message = self.mq.wait_and_dequeue(session=session, timeout=5)
            if message:
                self.handle_message(message, session=session)
                session.expunge(message)
        return message

    def _process_message(self, message):
        with get_session() as session:
            download_task = DownloadTaskSchema().load(json.loads(message.body), session=session)
            logger.info(f"下载视频开始, channel: {download_task.channel_name}, video: {download_task.url}")
            download_task.status = 'DOWNLOADING'
            session.commit()
            session.expunge(download_task)
        return download_task

    def _download_video(self, download_task):
        return Downloader.download(download_task.task_id, download_task.url, self.get_queue_thread_name())

    def _update_task_status(self, download_task, status):
        with get_session() as session:
            download_task = session.query(DownloadTask).where(
                DownloadTask.task_id == download_task.task_id).one()

            if status == 0:
                self._handle_completed_download(download_task, session)
            elif status == 1:
                download_task.status = 'FAILED'
            elif status == 2:
                download_task.status = 'PAUSED'

            session.commit()
            session.expunge(download_task)

    def _handle_completed_download(self, download_task, session):
        download_task.status = 'COMPLETED'
        download_task.error_message = ''
        session.commit()

        channel_video = session.query(ChannelVideo).where(
            ChannelVideo.video_id == download_task.video_id).first()
        if channel_video:
            channel_video.if_downloaded = True
            session.commit()

        self._update_redis_cache(download_task)

    def _update_redis_cache(self, download_task):
        key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{download_task.domain}:{download_task.video_id}"
        client = RedisClient.get_instance().client
        client.hset(key, 'if_download', datetime.now().timestamp())

    def _handle_error(self, e, message, task_id):
        logger.error(
            f"处理消息时发生错误: {e}, message: {MessageSchema().dumps(message)}",
            exc_info=True)
        if task_id:
            with get_session() as session:
                download_task = session.query(DownloadTask).where(
                    DownloadTask.task_id == task_id).first()
                download_task.status = 'FAILED'
                download_task.error_message = str(e)
                session.commit()
