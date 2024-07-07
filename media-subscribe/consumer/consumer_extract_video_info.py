import json
import logging

from common.constants import QUEUE_DOWNLOAD_TASK
from common.database import get_session
from common.message_queue import RedisMessageQueue
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.download_task import DownloadTask, DownloadTaskSchema
from model.message import Message

logger = logging.getLogger(__name__)


class ExtractorInfoTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            download_task = None
            with get_session() as session:
                try:
                    message = self.mq.wait_and_dequeue(session=session, timeout=None)
                    if message:
                        session.query(Message).filter(Message.message_id == message.message_id,
                                                      Message.send_status == 'SENDING').update(
                            {'send_status': 'SUCCESS'})
                        session.commit()

                        download_task = DownloadTaskSchema().load(json.loads(message.body), session=session)

                        video_info = Downloader.get_video_info(download_task.url)
                        if video_info is None:
                            continue

                        # 不支持playlist
                        if '_type' in video_info and video_info['_type'] == 'playlist':
                            session.query(DownloadTask).filter(DownloadTask.task_id == download_task.task_id).update(
                                {'status': 'UNSUPPORTED', 'title': video_info['title']})
                            session.commit()
                            continue

                        thumbnail = video_info['thumbnail']
                        download_task.status = 'WAITING'
                        session.query(DownloadTask).filter(DownloadTask.task_id == download_task.task_id,
                                                           DownloadTask.status == 'PENDING').update(
                            {'status': 'WAITING', 'thumbnail': thumbnail, 'title': video_info['title']})
                        session.commit()

                        message = Message()
                        message.body = DownloadTaskSchema().dumps(download_task)
                        session.add(message)
                        session.commit()

                        RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)
                        session.query(Message).filter(Message.message_id == message.message_id, Message.send_status == 'PENDING').update({'send_status': 'SENDING'})

                        session.commit()

                        download_task = None
                except Exception as e:
                    logger.error(f"处理消息时发生错误: {e}", exc_info=True)
                    if download_task:
                        session.query(Message).filter(Message.message_id == download_task.task_id).update({'send_status': 'FAILED'})
                        session.commit()
