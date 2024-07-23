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
                with get_session() as session:
                    message = self.mq.wait_and_dequeue(session=session, timeout=5)
                    if message:
                        self.handle_message(message, session)

                        url = json.loads(message.body)['url']
                        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
                        channel_info = subscribe_channel.get_channel_info()

                        channel = session.query(Channel).filter(Channel.channel_id == channel_info.id,
                                                                Channel.name == channel_info.name).first()
                        if channel:
                            logger.info(f"频道 {channel_info.name} 已存在")
                            continue

                        channel = Channel()
                        channel.channel_id = channel_info.id
                        channel.name = channel_info.name
                        channel.url = channel_info.url
                        channel.avatar = channel_info.avatar

                        videos = subscribe_channel.get_channel_videos(channel, update_all=True)
                        channel.total_videos = len(videos)

                        session.add(channel)
                        session.commit()

            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
