import logging

import dramatiq

from common import constants
from dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService

logger = logging.getLogger()


@dramatiq.actor(queue_name=constants.QUEUE_SUBSCRIPTION_UPDATE)
def process_subscription_update(message):
    try:
        logger.info(f"Processing subscription update message: {message}")
        message_obj = Message.from_dict(message)
        params = SubscriptionUpdateDto.model_validate_json(message_obj.body)
        sub = subscription_service.get_subscription_detail(params.subscription_id)
        if not sub or sub.is_deleted:
            logger.info(f"Subscription {params.subscription_id} not found or deleted")
            return
        SubscriptionUpdateService.update_subscription_videos(sub)
    except Exception as e:
        logger.error(f"Error processing subscription update: {e}", exc_info=True)

