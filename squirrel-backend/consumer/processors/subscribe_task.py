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
from subscribe.factory import SubscriptionFactory
from consumer.queue_management.decorators import queue_handler
from consumer.queue_management.manager import QueueManager

logger = logging.getLogger(__name__)


@queue_handler(constants.QUEUE_SUBSCRIBE)
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
            return {"status": "already_subscribed", "subscription_id": subscription.id}

        if subscription and subscription.is_deleted:
            # 恢复已删除的订阅
            _restore_deleted_subscription(subscription, user_id)
            logger.info(f"恢复已删除的订阅: {subscription.name}")
            return {"status": "restored", "subscription_id": subscription.id}
        else:
            # 创建新订阅
            subscription = subscription_service.create_subscription(user_id, subscribe_info)
            logger.info(f"成功创建新订阅: {subscription.name}")
            return {"status": "created", "subscription_id": subscription.id}

    except Exception as e:
        logger.error(f"处理订阅时发生错误: {e}", exc_info=True)
        raise


@queue_handler("subscription_batch")
def process_batch_subscribe(message: Dict[str, Any]):
    try:
        urls = message['urls']
        user_id = message['user_id']
        batch_id = message.get('batch_id', 'unknown')

        logger.info(f"开始批量订阅: batch_id={batch_id}, 频道数={len(urls)}")

        results = []
        for url in urls:
            try:
                subscribe_message = {
                    "body": json.dumps({
                        "url": url,
                        "user_id": user_id
                    })
                }

                QueueManager.send_message(constants.QUEUE_SUBSCRIBE, subscribe_message)
                results.append({"url": url, "status": "queued"})

            except Exception as e:
                logger.error(f"批量订阅中单个URL失败: url={url}, error={e}")
                results.append({"url": url, "status": "failed", "error": str(e)})

        success_count = len([r for r in results if r['status'] == 'queued'])
        logger.info(f"批量订阅完成: batch_id={batch_id}, 成功={success_count}/{len(urls)}")

        return {
            "batch_id": batch_id,
            "total": len(urls),
            "success": success_count,
            "failed": len(urls) - success_count,
            "results": results
        }

    except Exception as e:
        logger.error(f"批量订阅失败: {e}", exc_info=True)
        raise


@queue_handler("subscription_verify")
def process_subscription_verification(message: Dict[str, Any]):
    try:
        subscription_id = message['subscription_id']

        logger.info(f"开始验证订阅: subscription_id={subscription_id}")

        subscription = subscription_service.get_subscription_by_id(subscription_id)
        if not subscription or subscription.is_deleted:
            logger.warning(f"订阅不存在或已删除: subscription_id={subscription_id}")
            return {"status": "not_found"}

        try:
            subscribe_channel = SubscriptionFactory.create_subscription(subscription.url)
            subscribe_info = subscribe_channel.get_subscribe_info()

            if subscribe_info.name != subscription.name or subscribe_info.avatar != subscription.avatar:
                subscription_service.update_subscription_info(
                    subscription_id,
                    subscribe_info.name,
                    subscribe_info.avatar
                )
                logger.info(f"更新订阅信息: {subscription.name}")

            return {"status": "valid", "updated": True}

        except Exception as e:
            logger.warning(f"订阅验证失败，可能已失效: subscription_id={subscription_id}, error={e}")
            return {"status": "invalid", "error": str(e)}

    except Exception as e:
        logger.error(f"订阅验证处理失败: {e}", exc_info=True)
        raise


def _restore_deleted_subscription(subscription: Subscription, user_id: int):
    """恢复已删除的订阅"""
    with get_session() as session:
        # 恢复订阅
        session.query(Subscription).filter(Subscription.id == subscription.id).update({
            Subscription.is_deleted: 0
        })

        # 检查用户订阅关联
        user_subscription = session.scalars(select(UserSubscription).where(
            UserSubscription.subscription_id == subscription.id,
            UserSubscription.user_id == user_id
        )).first()

        if user_subscription and user_subscription.is_deleted:
            # 恢复用户订阅关联
            session.query(UserSubscription).where(UserSubscription.id == user_subscription.id).update({
                UserSubscription.is_deleted: 0
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

