import json
import logging

from common.database import get_session
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.channel import ChannelVideo
from model.download_task import DownloadTaskSchema
from model.message import MessageSchema

logger = logging.getLogger(__name__)


class DownloadTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            message = None
            download_task = None
            with get_session() as session:
                try:
                    message = self.mq.wait_and_dequeue(session=session, timeout=5)
                    if message:
                        self.handle_message(message, session)
                        download_task = DownloadTaskSchema().load(json.loads(message.body), session=session)
                        logger.info(f"下载视频开始, channel: {download_task.channel_name}, video: {download_task.url}")

                        download_task.status = 'DOWNLOADING'
                        session.commit()
                        Downloader.download(download_task.url)
                        download_task.status = 'COMPLETED'
                        download_task.error_message = ''
                        session.commit()
                        channel_video = session.query(ChannelVideo).where(ChannelVideo.video_id == download_task.video_id).one()
                        if channel_video:
                            channel_video.if_downloaded = True
                            session.commit()

                        logger.info(f"下载视频结束, channel: {download_task.channel_name}, video: {download_task.url}")
                        download_task = None

                except Exception as e:
                    logger.error(
                        f"处理消息时发生错误: {e}, message: {MessageSchema().dumps(message)}",
                        exc_info=True)
                    if download_task:
                        download_task.status = 'FAILED'
                        download_task.error_message = str(e)
                        session.commit()
