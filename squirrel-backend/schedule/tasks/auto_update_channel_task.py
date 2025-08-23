import logging
from sqlalchemy import select
from common import constants
from core.cache import RedisClient
from core.config import settings
from core.database import get_session
from models.subscription import Subscription
from mq import RedisStreamProducer
from schedule.task import TaskRegistry, BaseTask
from services import subscription_service

logger = logging.getLogger()
client = RedisClient.get_instance().get_client()


@TaskRegistry.register(interval=10, unit='minutes')
class AutoUpdateChannelVideo(BaseTask):
    """
    Scheduler scans subscriptions and enqueues update messages with backlog guard,
    subscription-level enqueue dedupe, and simple cursor-based batching.
    """

    @classmethod
    def run(cls):
        try:
            # Backpressure: skip when backlog high
            try:
                qlen_raw = client.xlen(constants.QUEUE_SUBSCRIPTION_UPDATE)
                qlen = int(qlen_raw) if isinstance(qlen_raw, (int, str)) else 0
            except Exception:
                qlen = 0
            if qlen > settings.SUB_UPDATE_BACKLOG_MAX:
                logger.warning(f"Backlog high ({qlen}), skip this tick")
                return

            # Cursor-based batching
            cursor_key = "subscription:schedule:cursor"
            try:
                last_id_raw = client.get(cursor_key)
                last_id = int(last_id_raw) if isinstance(last_id_raw, (int, str)) else 0
            except Exception:
                last_id = 0

            with get_session() as session:
                batch = session.scalars(
                    select(Subscription)
                    .where(Subscription.is_deleted == False, Subscription.id > last_id)
                    .order_by(Subscription.id.asc())
                    .limit(settings.SUB_UPDATE_BATCH_SIZE)
                ).all()
                # If reached end, wrap around from beginning
                if not batch:
                    batch = session.scalars(
                        select(Subscription)
                        .where(Subscription.is_deleted == False)
                        .order_by(Subscription.id.asc())
                        .limit(settings.SUB_UPDATE_BATCH_SIZE)
                    ).all()

            from services import message_service
            enqueued = 0
            for sub in batch:
                try:
                    sub_detail = subscription_service.get_subscription_by_id(sub.id)
                    content = {
                        "subscription_id": getattr(sub_detail, 'id', sub.id),
                        "url": getattr(sub_detail, 'url', ''),
                        "total_videos": getattr(sub_detail, 'total_videos', 0),
                        "total_extract": getattr(sub_detail, 'total_extract', 0),
                        "is_nsfw": getattr(sub_detail, 'is_nsfw', False),
                    }
                    message = message_service.create_message(content)
                    # Send to scheduled entry queue; entry consumer will route & dedupe
                    RedisStreamProducer().send(constants.QUEUE_SUBSCRIPTION_UPDATE, message.to_dict())
                    enqueued += 1
                except Exception as e:
                    logger.error(f"Failed to enqueue update for subscription {sub.id}: {e}", exc_info=True)

            # Advance cursor
            if batch:
                try:
                    client.set(cursor_key, batch[-1].id)
                except Exception:
                    pass
            logger.info(f"AutoUpdateChannelVideo: enqueued {enqueued} subscriptions")
        except Exception as e:
            logger.error(f"AutoUpdateChannelVideo.run unexpected error: {e}", exc_info=True)

    @classmethod
    def shutdown(cls):
        pass
