import json
import logging
import dramatiq
from common import constants
from core.database import get_session
from models.message import Message
from models.subscription import Subscription
from services import subscription_service
from subscribe.factory import SubscriptionFactory

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_SUBSCRIBE)
def process_subscribe_message(message):
    try:
        logger.info(f"Received subscription message: {message}")
        message_obj = Message.from_dict(message)
        url = json.loads(message_obj.body)['url']
        user_id = json.loads(message_obj.body)['user_id']
        subscribe_channel = SubscriptionFactory.create_subscription(url)
        subscribe_info = subscribe_channel.get_subscribe_info()

        subscription = subscription_service.get_subscription_by_url_and_name(url, subscribe_info.name)
        if subscription and not subscription.is_deleted:
            logger.info(f"Already subscribed to this channel: {subscription.name}")
            return
        if subscription and subscription.is_deleted:
            with get_session() as session:
                session.query(Subscription).filter(Subscription.id == subscription.id).update({
                    Subscription.is_deleted: 0
                })
                session.commit()
        else:
            subscription_service.create_subscription(user_id, subscribe_info)
        logger.info(f"Successfully subscribed: {subscription.name}")
    except Exception as e:
        logger.error(f"Error occurred while adding subscription: {e}", exc_info=True)
