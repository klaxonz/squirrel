import json
import logging

from common.constants import QUEUE_DOWNLOAD_TASK
from common.database import get_session
from common.message_queue import RedisMessageQueue
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from meta.video import VideoFactory
from model.download_task import DownloadTaskSchema
from model.message import Message

logger = logging.getLogger(__name__)


class ExtractorInfoTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            download_task = None
            with get_session() as session:
                try:
                    message = self.mq.wait_and_dequeue(session=session, timeout=5)
                    if message:
                        message.send_status = 'SUCCESS'
                        session.commit()

                        download_task = DownloadTaskSchema().load(json.loads(message.body), session=session)

                        video_info = Downloader.get_video_info(download_task.url)
                        if video_info is None:
                            continue
                        video = VideoFactory.create_video(download_task.url, video_info)
                        download_task.title = video.get_title()
                        download_task.channel_id = video.get_uploader().id
                        download_task.channel_url = video.get_uploader().url
                        download_task.channel_name = video.get_uploader().name
                        download_task.channel_avatar = video.get_uploader().avatar

                        # 不支持playlist
                        if '_type' in video_info and video_info['_type'] == 'playlist':
                            download_task.status = 'UNSUPPORTED'
                            session.commit()
                            continue

                        thumbnail = video_info['thumbnail']
                        download_task.status = 'WAITING'
                        download_task.thumbnail = thumbnail
                        session.commit()

                        message = Message()
                        message.body = DownloadTaskSchema().dumps(download_task)
                        session.add(message)
                        session.commit()

                        RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)
                        message.send_status = 'SENDING'
                        session.commit()

                        download_task = None
                except Exception as e:
                    logger.error(f"处理消息时发生错误: {e}", exc_info=True)
                    if download_task:
                        download_task.status = 'FAILED'
                        session.commit()
