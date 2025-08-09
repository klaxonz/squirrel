import logging
from typing import Dict, Any
from common import constants
from consumer.queue_management.decorators import queue_handler
from dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService

logger = logging.getLogger(__name__)


@queue_handler(constants.QUEUE_SUBSCRIPTION_UPDATE)
def process_subscription_update(message: Dict[str, Any]):
    try:
        logger.info(f"开始处理订阅更新消息: {message}")

        message_obj = Message.from_dict(message)
        params = SubscriptionUpdateDto.model_validate_json(message_obj.body)

        sub = subscription_service.get_subscription_detail(params.subscription_id)
        if not sub or getattr(sub, 'is_deleted', False):
            logger.info(f"订阅不存在或已删除: subscription_id={params.subscription_id}")
            return None

        SubscriptionUpdateService.update_subscription_videos(sub)

        sub_name = getattr(sub, 'name', f'subscription_{params.subscription_id}')
        logger.info(f"订阅更新完成: {sub_name}, subscription_id={params.subscription_id}")

        return None

    except Exception as e:
        logger.error(f"处理订阅更新时发生错误: {e}", exc_info=True)
        raise

