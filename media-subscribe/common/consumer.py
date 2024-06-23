import logging
import threading
import time

from downloader.downloader import Downloader
from downloader.id_extractor import extract_id_from_url
from subscribe.subscribe import SubscribeChannelFactory
from model.task import Task
from model.channel import Channel
from .cache import RedisClient
from .cookie import extract_top_level_domain
from .message_queue import RedisMessageQueue

logger = logging.getLogger(__name__)


class DownloadTaskConsumerThread(threading.Thread):
    def __init__(self, queue_name):
        super().__init__()
        self.queue_name = queue_name
        self.running = True

    def run(self):
        key = ''
        client = RedisClient.get_instance().client
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

                    # 设置 redis key
                    domain = extract_top_level_domain(url)
                    video_id = extract_id_from_url(url)
                    key = f"task:{domain}:{video_id}"

                    task_status = client.hgetall(key)
                    if task_status and (
                            'status' in task_status and task_status['status'] in ['downloading', 'success']):
                        continue

                    # 设置key
                    client.hmset(key, {"status": "downloading", "start_at": time.time()})

                    Task.mark_as_in_progress(message.message_id)
                    Downloader.download(url)
                    Task.mark_as_completed(message.message_id)

                    client.hmset(key, {"status": "success", "end_at": time.time()})

                    key = ''
            except Exception as e:
                if key:
                    client.hmset(key, {"status": "failed", "end_at": time.time()})
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
