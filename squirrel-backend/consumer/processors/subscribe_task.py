import json
import logging
from typing import Dict, Any
from sqlalchemy import select
from common import constants
from core.database import get_session
from models.links import UserSubscription
from models.message import Message
from models.subscription import Subscription
from services import subscription_service
from sites.subscription import SubscriptionFactory
from mq import mq_consumer

logger = logging.getLogger(__name__)


@mq_consumer(constants.QUEUE_SUBSCRIBE, group="subscription", consumer_name="subscribe")
def process_subscribe_message(message: Dict[str, Any]):
    try:
        logger.info(f"收到订阅消息: {message}")

        message_obj = Message.from_dict(message)
        body_data = json.loads(message_obj.body)
        url = body_data['url']
        user_id = body_data['user_id']

        subscribe_channel = SubscriptionFactory.create_subscription(url)
        subscribe_info = subscribe_channel.get_subscribe_info()

        subscription = subscription_service.get_subscription_by_url_and_name(url, subscribe_info.name)

        if subscription and not subscription.is_deleted:
            logger.info(f"已经订阅了此频道: {subscription.name}")
            return

        if subscription and subscription.is_deleted:
            # 恢复已删除的订阅
            _restore_deleted_subscription(subscription, user_id)
            logger.info(f"恢复已删除的订阅: {subscription.name}")
            return
        else:
            # 创建新订阅
            subscription = subscription_service.create_subscription(user_id, subscribe_info)
            logger.info(f"成功创建新订阅: {subscription.name}")
            return

    except Exception as e:
        logger.error(f"处理订阅时发生错误: {e}", exc_info=True)
        raise


def _restore_deleted_subscription(subscription: Subscription, user_id: int):
    """恢复已删除的订阅"""
    with get_session() as session:
        # 恢复订阅
        session.query(Subscription).filter(Subscription.id == subscription.id).update({
            Subscription.is_deleted: False
        })

        # 检查用户订阅关联
        user_subscription = session.scalars(select(UserSubscription).where(
            UserSubscription.subscription_id == subscription.id,
            UserSubscription.user_id == user_id
        )).first()

        if user_subscription and user_subscription.is_deleted:
            # 恢复用户订阅关联
            session.query(UserSubscription).where(UserSubscription.id == user_subscription.id).update({
                UserSubscription.is_deleted: False
            })
        elif not user_subscription:
            # 创建新的用户订阅关联
            user_subscription = UserSubscription(
                subscription_id=subscription.id,
                user_id=user_id,
                is_deleted=False
            )
            session.add(user_subscription)

        session.commit()

