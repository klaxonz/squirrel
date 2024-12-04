import json
import logging

import dramatiq
from sqlmodel import select

from common import constants
from core.database import get_session
from model.channel import Channel
from model.message import Message
from subscribe.subscribe import SubscribeChannelFactory

logger = logging.getLogger(__name__)


@dramatiq.actor(queue_name=constants.QUEUE_SUBSCRIBE_TASK)
def process_subscribe_message(message):
    try:
        logger.info(f"开始处理订阅频道消息：{message}")
        if not message or message == '{}':
            return
        logger.info(f"收到订阅频道消息: {message}")
        message_obj = Message.model_validate(json.loads(message))
        url = _extract_url(message_obj)
        subscribe_channel = SubscribeChannelFactory.create_subscribe_channel(url)
        channel_info = subscribe_channel.get_channel_info()

        if _channel_exists(channel_info):
            logger.info(f"频道 {channel_info.name} 已存在")
            return
        logger.info(f"开始添加新频道: {channel_info.name}")

        with get_session() as session:
            channel = _create_channel(channel_info)
            session.add(channel)
            session.commit()

            videos = subscribe_channel.get_channel_videos(channel, update_all=True)
            channel.total_videos = len(videos)
            session.commit()

            logger.info(f"成功添加新频道: {channel.name}")
    except Exception as e:
        logger.error(f"处理订阅频道消息时发生错误: {e}", exc_info=True)


def _extract_url(message):
    return json.loads(message.body)['url']


def _channel_exists(channel_info):
    with get_session() as session:
        return session.exec(select(Channel).where(
            Channel.channel_id == channel_info.id,
            Channel.name == channel_info.name
        )).first() is not None


def _create_channel(channel_info):
    channel = Channel()
    channel.channel_id = channel_info.id
    channel.name = channel_info.name
    channel.url = channel_info.url
    channel.avatar = channel_info.avatar
    channel.if_extract_all = 0
    return channel


def _save_channel(channel):
    with get_session() as session:
        session.add(channel)
        session.commit()
