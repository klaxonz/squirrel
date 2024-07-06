import json
import logging
import threading
from datetime import datetime

from playhouse.shortcuts import dict_to_model, model_to_dict

from downloader.downloader import Downloader
from model.download_task import DownloadTask
from model.message import Message
from schedule.schedule import AutoUpdateChannelVideoTask
from service import download_service
from subscribe.subscribe import SubscribeChannelFactory
from model.channel import Channel, ChannelVideo
from utils import json_serialize
from .cache import RedisClient
from .constants import QUEUE_DOWNLOAD_TASK
from .message_queue import RedisMessageQueue

logger = logging.getLogger(__name__)


class BaseConsumerThread(threading.Thread):
    """Base class for consumer threads to handle common setup and teardown."""

    def __init__(self, queue_name):
        super().__init__()
        self.queue_name = queue_name
        self.running = True
        self.redis = RedisClient.get_instance().client  # Cache Redis client instance
        self.mq = RedisMessageQueue(queue_name=self.queue_name)  # Initialize MQ once

    def handle_message(self, message):
        """Handle a generic message pattern to reduce duplication."""
        try:
            Message.update(send_status='SUCCESS').where(Message.message_id == message.message_id,
                                                        Message.send_status == 'SENDING').execute()
        except Exception as e:
            logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    def stop(self):
        self.running = False


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


class ExtractorChannelVideoConsumerThread(BaseConsumerThread):
    def run(self):
        while self.running:
            try:
                message = self.mq.wait_and_dequeue(timeout=None)
                if message:
                    self.handle_message(message)

                    channel_video = dict_to_model(ChannelVideo, json.loads(message.body))

                    key = f"task:extract:{channel_video.domain}:{channel_video.channel_id}:{channel_video.video_id}"
                    if self.redis.exists(key):
                        continue

                    video_info = Downloader.get_video_info(channel_video.url)
                    if video_info is None:
                        continue
                    if '_type' in video_info and video_info['_type'] == 'playlist':
                        continue

                    uploaded_time = datetime.fromtimestamp(int(video_info['timestamp']))
                    thumbnail = video_info['thumbnail']

                    ChannelVideo.update(title=video_info['title'], thumbnail=thumbnail,
                                        uploaded_at=uploaded_time).where(
                        ChannelVideo.channel_id == channel_video.channel_id,
                        ChannelVideo.video_id == channel_video.video_id).execute()

                    self.redis.set(key, channel_video.video_id, 12 * 60 * 60)
                    channel = Channel.select().where(Channel.channel_id == channel_video.channel_id).first()
                    if channel.if_auto_download:
                        download_service.start_download(channel_video.url)
                        ChannelVideo.update(if_downloaded=True).where(ChannelVideo.video_id == channel_video.video_id,
                                                                      ChannelVideo.channel_id == channel_video.channel_id).execute()

            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)


class DownloadTaskConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            message = None
            download_task = None
            try:
                message = self.mq.wait_and_dequeue(timeout=None)
                if message:
                    self.handle_message(message)

                    download_task = dict_to_model(DownloadTask, json.loads(message.body))
                    key = f"task:{download_task.domain}:{download_task.video_id}"

                    if self.redis.exists(key):
                        continue

                    DownloadTask.update(status='DOWNLOADING').where(
                        DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'WAITING').execute()

                    Downloader.download(download_task.url)

                    DownloadTask.update(status='COMPLETED').where(
                        DownloadTask.task_id == download_task.task_id, DownloadTask.status == 'DOWNLOADING').execute()

                    # 写入缓存
                    self.redis.set(key, download_task.video_id, 12 * 60 * 60)

                    download_task = None
            except Exception as e:
                logger.error(
                    f"处理消息时发生错误: {e}, message: {json.dumps(model_to_dict(message), default=json_serialize.more)}",
                    exc_info=True)
                if download_task:
                    DownloadTask.update(status='FAILED', error_message=str(e)).where(
                        DownloadTask.task_id == download_task.task_id).execute()


class SubscribeChannelConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            message = None
            try:
                message = self.mq.wait_and_dequeue(timeout=None)
                if message:
                    self.handle_message(message)

                    url = json.loads(message.body)['url']
                    subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
                    channel_info = subscribe_channel.get_channel_info()
                    Channel.subscribe(channel_info.id, channel_info.name, channel_info.url)
                    AutoUpdateChannelVideoTask.run()

            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
