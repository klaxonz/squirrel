import json
import logging

from .message_queue import RedisMessageQueue
import threading
from downloader.downloader import Downloader
from model.task import Task

logger = logging.getLogger(__name__)


class DownloadTaskConsumerThread(threading.Thread):
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
                    url = message.content.get("url")
                    task = Task.get_task(message.message_id)
                    if task and task.status is Task.STATUS_IN_PROGRESS:
                        continue

                    Task.mark_as_in_progress(message.message_id)
                    Downloader.download(url)
                    Task.mark_as_completed(message.message_id)

            except Exception as e:
                if message:
                    Task.mark_as_failed(message.message_id)
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)

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
                    # 获取视频信息
                    video_info = Downloader.get_video_info(url)

                    Task.mark_as_completed(message.message_id)

            except Exception as e:
                if message:
                    Task.mark_as_failed(message.message_id)
                print(f"处理消息时发生错误: {e}")

    def stop(self):
        self.running = False
