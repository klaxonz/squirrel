import logging
from sqlalchemy import select, func
from common import constants
from core.database import get_session
from models.subscription import Subscription
from models.links import SubscriptionVideo
from mq import RedisStreamProducer
from schedule.task import TaskRegistry, BaseTask
from services import message_service

logger = logging.getLogger()

BATCH_SIZE = 100


@TaskRegistry.register(interval=300, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    """
    定时扫描所有订阅，将更新任务发送到消息队列
    采用分批处理策略，避免大量订阅时的内存问题
    """

    @classmethod
    def run(cls):
        try:
            total_subscriptions = cls._get_total_subscriptions()
            if total_subscriptions == 0:
                logger.info("No active subscriptions found, skipping update task")
                return

            logger.info(f"Starting subscription update task, total subscriptions: {total_subscriptions}")
            
            success_count = 0
            error_count = 0
            
            offset = 0
            while offset < total_subscriptions:
                batch_subscriptions = cls._fetch_subscription_batch(offset, BATCH_SIZE)
                
                for sub in batch_subscriptions:
                    try:
                        cls._enqueue_subscription_update(sub)
                        success_count += 1
                    except Exception as e:
                        error_count += 1
                        logger.error(
                            f"Failed to enqueue update for subscription {sub.id} ({sub.name}): {e}",
                            exc_info=True
                        )
                
                offset += BATCH_SIZE
                logger.debug(f"Processed {min(offset, total_subscriptions)}/{total_subscriptions} subscriptions")
            
            logger.info(
                f"Subscription update task completed. "
                f"Success: {success_count}, Failed: {error_count}, Total: {total_subscriptions}"
            )
            
        except Exception as e:
            logger.error(f"AutoUpdateChannelVideo.run unexpected error: {e}", exc_info=True)

    @classmethod
    def _get_total_subscriptions(cls) -> int:
        with get_session() as session:
            count = session.execute(
                select(func.count(Subscription.id))
                .where(Subscription.is_deleted == False)
            ).scalar() or 0
            return count

    @classmethod
    def _fetch_subscription_batch(cls, offset: int, limit: int) -> list[Subscription]:
        with get_session() as session:
            subscriptions = session.scalars(
                select(Subscription)
                .where(Subscription.is_deleted == False)
                .order_by(Subscription.id.asc())
                .limit(limit)
                .offset(offset)
            ).all()
            return subscriptions

    @classmethod
    def _enqueue_subscription_update(cls, subscription: Subscription):
        content = {
            "subscription_id": subscription.id,
            "url": subscription.url or '',
        }
        
        message = message_service.create_message(content)
        RedisStreamProducer().send(constants.QUEUE_SUBSCRIPTION_UPDATE, message.to_dict())

    @classmethod
    def shutdown(cls):
        logger.info("AutoUpdateChannelVideo task shutdown")
        pass
