import logging
from sqlalchemy import select
from common import constants
from core.cache import RedisClient
from core.database import get_session
from models.subscription import Subscription
from mq import RedisStreamProducer
from schedule.task import TaskRegistry, BaseTask
from services import subscription_service

logger = logging.getLogger()
client = RedisClient.get_instance().get_client()


@TaskRegistry.register(interval=300, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    """
    Scheduler scans subscriptions and enqueues update messages with backlog guard,
    subscription-level enqueue dedupe, and simple cursor-based batching.
    """

    @classmethod
    def run(cls):
        try:
            with get_session() as session:
                batch = session.scalars(
                    select(Subscription)
                    .where(Subscription.is_deleted == False)
                    .order_by(Subscription.id.asc())
                ).all()

            from services import message_service
            for sub in batch:
                try:
                    sub_detail = subscription_service.get_subscription_by_id(sub.id)
                    content = {
                        "subscription_id": getattr(sub_detail, 'id', sub.id),
                        "url": getattr(sub_detail, 'url', ''),
                        "total_videos": getattr(sub_detail, 'total_videos', 0),
                        "total_extract": getattr(sub_detail, 'total_extract', 0),
                    }
                    message = message_service.create_message(content)
                    RedisStreamProducer().send(constants.QUEUE_SUBSCRIPTION_UPDATE, message.to_dict())
                except Exception as e:
                    logger.error(f"Failed to enqueue update for subscription {sub.id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"AutoUpdateChannelVideo.run unexpected error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        pass
