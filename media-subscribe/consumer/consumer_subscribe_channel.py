import json
import logging

from consumer.base import BaseConsumerThread
from model.channel import Channel
from schedule.schedule import AutoUpdateChannelVideoTask
from subscribe.subscribe import SubscribeChannelFactory

logger = logging.getLogger(__name__)


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
