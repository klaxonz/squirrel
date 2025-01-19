import json
import logging

import dramatiq
from sqlalchemy import select

from common import constants
from core.database import get_session
from models.message import Message
from models.subscription import Subscription, ContentType
from subscribe.factory import SubscriptionFactory

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_SUBSCRIBE)
def process_subscribe_message(message):
    try:
        logger.info(f"Received subscription message: {message}")
        message_obj = Message.from_dict(message)
        url = json.loads(message_obj.body)['url']
        subscribe_channel = SubscriptionFactory.create_subscription(url)
        channel_info = subscribe_channel.get_subscribe_info()
        videos = subscribe_channel.get_subscribe_videos(extract_all=True)

        with get_session() as session:
            subscription = session.scalars(select(Subscription).where(
                Subscription.url == channel_info.url,
                Subscription.name == channel_info.name
            )).first()
            if subscription and not subscription.is_deleted:
                logger.info(f"Already subscribed to this channel: {subscription.name}")
                return
            if subscription and subscription.is_deleted:
                subscription.total_videos = len(videos)
                subscription.is_deleted = False
            else:
                subscription = _create_subscription(channel_info)
                subscription.total_videos = len(videos)
                session.add(subscription)
            session.commit()
            logger.info(f"Successfully subscribed: {subscription.name}")
    except Exception as e:
        logger.error(f"Error occurred while adding subscription: {e}", exc_info=True)


def _create_subscription(channel_info):
    subscription = Subscription(
        type=ContentType.CHANNEL,
        name=channel_info.name,
        url=channel_info.url,
        avatar=channel_info.avatar,
        description=None,
        extra_data={}
    )
    return subscription
