import json
import logging

from common.database import get_session
from consumer.base import BaseConsumerThread
from model.channel import Channel
from subscribe.subscribe import SubscribeChannelFactory

logger = logging.getLogger(__name__)


class SubscribeChannelConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            try:
                message = self._dequeue_message()
                if message:
                    self._process_message(message)
            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)

    def _dequeue_message(self):
        with get_session() as session:
            message = self.mq.wait_and_dequeue(session=session, timeout=5)
            if message:
                self.handle_message(message, session=session)
                session.expunge(message)
        return message

    def _process_message(self, message):
        url = json.loads(message.body)['url']
        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
        channel_info = subscribe_channel.get_channel_info()

        if self._channel_exists(channel_info):
            return

        channel = self._create_channel(channel_info)
        videos = subscribe_channel.get_channel_videos(channel, update_all=True)
        channel.total_videos = len(videos)

        self._save_channel(channel)

    def _channel_exists(self, channel_info):
        with get_session() as session:
            channel = session.query(Channel).filter(
                Channel.channel_id == channel_info.id,
                Channel.name == channel_info.name
            ).first()
            if channel:
                logger.info(f"频道 {channel_info.name} 已存在")
                return True
        return False

    def _create_channel(self, channel_info):
        channel = Channel()
        channel.channel_id = channel_info.id
        channel.name = channel_info.name
        channel.url = channel_info.url
        channel.avatar = channel_info.avatar
        channel.if_extract_all = 0
        return channel

    def _save_channel(self, channel):
        with get_session() as session:
            session.add(channel)
            session.commit()