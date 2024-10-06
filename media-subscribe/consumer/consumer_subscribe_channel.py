import json
import logging

from common import constants
from common.database import get_session
from consumer.base import BaseConsumerThread
from consumer.decorators import ConsumerRegistry
from model.channel import Channel
from subscribe.subscribe import SubscribeChannelFactory

logger = logging.getLogger(__name__)

@ConsumerRegistry.register(queue_name=constants.QUEUE_SUBSCRIBE_TASK, num_threads=1)
class SubscribeChannelConsumerThread(BaseConsumerThread):

    def _process_message(self, message, session):
        try:
            url = self._extract_url(message)
            subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
            channel_info = subscribe_channel.get_channel_info()

            if self._channel_exists(channel_info, session):
                logger.info(f"频道 {channel_info.name} 已存在")
                return

            channel = self._create_channel(channel_info)
            videos = subscribe_channel.get_channel_videos(channel, update_all=True)
            channel.total_videos = len(videos)

            self._save_channel(channel, session)
            logger.info(f"成功添加新频道: {channel.name}")
        except Exception as e:
            logger.error(f"处理订阅频道消息时发生错误: {e}", exc_info=True)

    def _extract_url(self, message):
        return json.loads(message.body)['url']

    def _channel_exists(self, channel_info, session):
        return session.query(Channel).filter(
            Channel.channel_id == channel_info.id,
            Channel.name == channel_info.name
        ).first() is not None

    def _create_channel(self, channel_info):
        channel = Channel()
        channel.channel_id = channel_info.id
        channel.name = channel_info.name
        channel.url = channel_info.url
        channel.avatar = channel_info.avatar
        channel.if_extract_all = 0
        return channel

    def _save_channel(self, channel, session):
        session.add(channel)
        session.commit()
