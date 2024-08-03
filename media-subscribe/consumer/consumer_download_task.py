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
                with get_session() as session:
                    message = self.mq.wait_and_dequeue(session=session, timeout=5)
                    if message:
                        self.handle_message(message, session=session)
                        session.expunge(message)
                if message:
                    with get_session() as session:
                        download_task = DownloadTaskSchema().load(json.loads(message.body), session=session)
                        logger.info(f"下载视频开始, channel: {download_task.channel_name}, video: {download_task.url}")
                        download_task.status = 'DOWNLOADING'
                        session.commit()
                        session.expunge(download_task)

                    status = Downloader.download(download_task.task_id, download_task.url, self.get_queue_thread_name())

                    with get_session() as session:
                        download_task = session.query(DownloadTask).where(
                            DownloadTask.task_id == download_task.task_id).one()
                        task_id = download_task.task_id
                        if status == 0:
                            download_task.status = 'COMPLETED'
                            download_task.error_message = ''
                            session.commit()
                            channel_video = session.query(ChannelVideo).where(
                                ChannelVideo.video_id == download_task.video_id).first()
                            if channel_video:
                                channel_video.if_downloaded = True
                                session.commit()

                            key = f"{constants.REDIS_KEY_VIDEO_DOWNLOAD_CACHE}:{download_task.domain}:{download_task.video_id}"
                            client = RedisClient.get_instance().client
                            client.hset(key, 'if_download', datetime.now().timestamp())

                        elif status == 1:
                            download_task.status = 'FAILED'
                            session.commit()
                        elif status == 2:
                            download_task.status = 'PAUSED'
                            session.commit()

                        session.expunge(download_task)

                    logger.info(f"下载视频结束, channel: {download_task.channel_name}, video: {download_task.url}")
                    task_id = None

            except Exception as e:
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
