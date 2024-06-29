import logging
import threading
import uuid

from downloader.downloader import Downloader
from model.download_task import json_to_downloadtask, DownloadTask
from model.message import Message
from subscribe.subscribe import SubscribeChannelFactory
from model.task import Task
from model.channel import Channel
from .cache import RedisClient
from .constants import QUEUE_DOWNLOAD_TASK, QUEUE_EXTRACT_TASK
from .message_queue import RedisMessageQueue

logger = logging.getLogger(__name__)


class ExtractorInfoTaskConsumerThread(threading.Thread):
    def __init__(self, queue_name):
        super().__init__()
        self.queue_name = queue_name
        self.running = True

    def run(self):
        mq = RedisMessageQueue(queue_name=self.queue_name)
        while self.running:
            download_task = None
            try:
                message = mq.wait_and_dequeue(timeout=None)
                if message:
                    message.send_status = 'SUCCESS'
                    message.save()

                    body = message.body
                    download_task = json_to_downloadtask(body)
                    download_task = DownloadTask.get_by_id(download_task.task_id)
                    if download_task is None:
                        return

                    url = download_task.url
                    video_info = Downloader.get_video_info(url)
                    download_task.title = video_info.title
                    download_task.save()

                    message_id = str(uuid.uuid4()).replace('-', '')
                    message_body = download_task.to_json()
                    message = Message(
                        message_id=message_id,
                        body=message_body
                    )
                    message.save()
                    RedisMessageQueue(queue_name=QUEUE_DOWNLOAD_TASK).enqueue(message)
                    Message.update(send_status='SENDING').where(message_id=message_id, send_status='PENDING').execute()

                    download_task = None
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
                if download_task:
                    download_task.status = 'FAILED'
                    download_task.error_message = str(e)
                    download_task.save()

    def stop(self):
        self.running = False


class DownloadTaskConsumerThread(threading.Thread):
    def __init__(self, queue_name):
        super().__init__()
        self.queue_name = queue_name
        self.running = True

    def run(self):
        client = RedisClient.get_instance().client
        mq = RedisMessageQueue(queue_name=self.queue_name)
        while self.running:
            download_task = None
            try:
                message = mq.wait_and_dequeue(timeout=None)
                if message:
                    message.send_status = 'SUCCESS'
                    message.save()

                    body = message.body
                    download_task = json_to_downloadtask(body)
                    url = download_task.url

                    video_info = Downloader.get_video_info(url)
                    download_task.title = video_info.title
                    download_task.status = 'DOWNLOADING'
                    download_task.save()

                    Downloader.download(url)

                    download_task.status = 'COMPLETED'
                    download_task.save()
                    download_task = None
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
                if download_task:
                    download_task.status = 'FAILED'
                    download_task.error_message = str(e)
                    download_task.save()

    def stop(self):
        self.running = False


class SubscribeChannelConsumerThread(threading.Thread):
    def __init__(self, queue_name):
        super().__init__()
        self.queue_name = queue_name
        self.running = True

    def run(self):
        mq = RedisMessageQueue(queue_name=self.queue_name)
        while self.running:
            message = None
            try:
                message = mq.wait_and_dequeue(timeout=None)
                if message:
                    task = Task.get_task(message.message_id)
                    if task and task.status is Task.STATUS_IN_PROGRESS:
                        continue

                    Task.mark_as_in_progress(message.message_id)
                    url = message.content.get("url")
                    subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
                    channel_info = subscribe_channel.get_channel_info()
                    Channel.subscribe(channel_info.id, channel_info.name, channel_info.url)

                    Task.mark_as_completed(message.message_id)

            except Exception as e:
                if message:
                    Task.mark_as_failed(message.message_id)
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    def stop(self):
        self.running = False
