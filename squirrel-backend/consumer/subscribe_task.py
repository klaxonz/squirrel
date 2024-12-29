import json
import logging

import dramatiq
from common import constants
from core.database import get_session
from models import Subscription, ContentType
from models.message import Message
from sqlmodel import select
from subscribe.factory import SubscriptionFactory

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_SUBSCRIBE_TASK)
def process_subscribe_message(message):
    try:
        logger.info(f"开始处理订阅频道消息：{message}")
        if not message or message == '{}':
            return
        logger.info(f"收到订阅频道消息: {message}")
        message_obj = Message.model_validate(json.loads(message))
        url = _extract_url(message_obj)
        subscribe_channel = SubscriptionFactory.create_subscription(url)
        channel_info = subscribe_channel.get_subscribe_info()

        subscription = get_subscription(channel_info)
        if subscription and not subscription.is_deleted:
            logger.info(f"已订阅过该频道: {subscription.name}")
            return
        if subscription and subscription.is_deleted:
            with get_session() as session:
                subscription = session.merge(subscription)
                subscription.is_deleted = False
                session.commit()
            logger.info(f"成功订阅: {channel_info.name}")
            return

        with get_session() as session:
            subscription = _create_subscription(channel_info)
            session.add(subscription)
            session.commit()
            logger.info(f"成功订阅: {subscription.content_name}")
    except Exception as e:
        logger.error(f"添加订阅时发生错误: {e}", exc_info=True)


def _extract_url(message):
    return json.loads(message.body)['url']


def get_subscription(channel_info):
    with get_session() as session:
        return session.exec(select(Subscription).where(
            Subscription.content_url == channel_info.url,
            Subscription.content_name == channel_info.name
        )).first()


def _create_subscription(channel_info):
    subscription = Subscription(
        content_type=ContentType.CHANNEL,
        content_name=channel_info.name,
        content_url=channel_info.url,
        avatar_url=channel_info.avatar,
        description=None,
        extra_data={}
    )
    return subscription
