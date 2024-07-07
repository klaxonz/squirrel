import json
import logging

from common.database import get_session
from consumer.base import BaseConsumerThread
from model.channel import Channel
from schedule.schedule import AutoUpdateChannelVideoTask
from subscribe.subscribe import SubscribeChannelFactory

logger = logging.getLogger(__name__)


class SubscribeChannelConsumerThread(BaseConsumerThread):

    def run(self):
        while self.running:
            try:
                with get_session() as session:
                    message = self.mq.wait_and_dequeue(session=session, timeout=None)
                    if message:
                        self.handle_message(message, session)

                        url = json.loads(message.body)['url']
                        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
                        channel_info = subscribe_channel.get_channel_info()

                        channel = Channel()
                        channel.channel_id = channel_info.id
                        channel.name = channel_info.name
                        channel.url = channel_info.url
                        session.add(channel)
                        session.commit()

                        AutoUpdateChannelVideoTask.run()

            except Exception as e:
                logger.error(f"处理消息时发生错误: {e}", exc_info=True)
