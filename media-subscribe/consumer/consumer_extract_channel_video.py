import json
import logging
from datetime import datetime
from playhouse.shortcuts import dict_to_model
from consumer.base import BaseConsumerThread
from downloader.downloader import Downloader
from model.channel import ChannelVideo, Channel
from service import download_service

logger = logging.getLogger(__name__)


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