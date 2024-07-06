import json
import logging

from playhouse.shortcuts import dict_to_model, model_to_dict

from common.constants import QUEUE_DOWNLOAD_TASK
from common.message_queue import RedisMessageQueue
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.download_task import DownloadTask
from model.message import Message
from utils import json_serialize

logger = logging.getLogger(__name__)


class ExtractorInfoTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            download_task = None
            try:
                message = self.mq.wait_and_dequeue(timeout=None)
                if message:
                    self.handle_message(message)

                    download_task = dict_to_model(DownloadTask, json.loads(message.body))
                    key = f"task:{download_task.domain}:{download_task.video_id}"

                    if self.redis.exists(key):
                        continue

                    video_info = Downloader.get_video_info(download_task.url)
                    if video_info is None:
                        continue

                    # 不支持playlist
                    if '_type' in video_info and video_info['_type'] == 'playlist':
                        DownloadTask.update(status='UNSUPPORTED', title=video_info['title']).where(
                            DownloadTask.task_id == download_task.task_id).execute()
                        continue

                    thumbnail = video_info['thumbnail']
                    DownloadTask.update(status='WAITING', thumbnail=thumbnail, title=video_info['title']).where(
                        DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'PENDING').execute()

                    message_body = json.dumps(model_to_dict(download_task), default=json_serialize.more)
                    message = Message(
                        body=message_body
                    )
                    message.save()

                    RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)
                    Message.update(send_status='SENDING').where(
                        Message.message_id == message.message_id, Message.send_status == 'PENDING').execute()

                    download_task = None
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
                if download_task:
                    DownloadTask.update(status='FAILED', error_message=str(e)).where(
                        DownloadTask.task_id == download_task.task_id).execute()
