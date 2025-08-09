import logging
from typing import Dict, Any
from datetime import datetime, timezone

from core.cache import RedisClient
from common import constants
from consumer.queue_management.decorators import queue_handler
from dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService

logger = logging.getLogger(__name__)
client = RedisClient.get_instance().get_client()


def _progress_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_UPDATE_PROGRESS_PREFIX}{sub_id}"


def _manual_flag_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_MANUAL_PENDING_PREFIX}{sub_id}"


def _set_progress(sub_id: int, data: Dict[str, Any]) -> None:
    base = {"subscriptionId": sub_id, "updatedAt": datetime.now(timezone.utc).isoformat()}
    client.hset(_progress_key(sub_id), mapping={**base, **data})
    client.expire(_progress_key(sub_id), 24 * 3600)


def _clear_manual_flag(sub_id: int) -> None:
    client.delete(_manual_flag_key(sub_id))


def _process_subscription_update(message: Dict[str, Any], is_manual: bool) -> None:
    source = "manual" if is_manual else "scheduled"
    logger.info(f"开始处理订阅更新消息({source}): {message}")
    message_obj = Message.from_dict(message)
    params = SubscriptionUpdateDto.model_validate_json(message_obj.body)

    # scheduled 消费者尊重 manual_pending 标记，存在则跳过
    if not is_manual:
        if client.exists(_manual_flag_key(params.subscription_id)):
            logger.info(f"手动更新占用中，跳过定时更新: subscription_id={params.subscription_id}")
            return

    sub = subscription_service.get_subscription_detail(params.subscription_id)
    if not sub or getattr(sub, 'is_deleted', False):
        logger.info(f"订阅不存在或已删除: subscription_id={params.subscription_id}")
        return

    # 进度 - 入场
    _set_progress(sub.id, {"status": "in_progress", "phase": "init", "source": source, "startedAt": datetime.now(timezone.utc).isoformat()})

    # manual 占用标记（短 TTL）
    if is_manual:
        client.set(_manual_flag_key(sub.id), 1, ex=120)

    try:
        SubscriptionUpdateService.update_subscription_videos(sub, is_manual=is_manual)
        sub_name = getattr(sub, 'name', f'subscription_{params.subscription_id}')
        logger.info(f"订阅更新完成: {sub_name}, subscription_id={params.subscription_id}")
        _set_progress(sub.id, {"status": "completed", "phase": "finalizing", "finishedAt": datetime.utcnow().isoformat()})
    except Exception as e:
        logger.error(f"订阅更新失败: subscription_id={params.subscription_id}, error={e}", exc_info=True)
        _set_progress(sub.id, {"status": "failed", "lastError": str(e)})
        raise
    finally:
        if is_manual:
            _clear_manual_flag(sub.id)


@queue_handler(constants.QUEUE_SUBSCRIPTION_UPDATE)
def process_subscription_update(message: Dict[str, Any]):
    try:
        _process_subscription_update(message, is_manual=False)
        return None
    except Exception as e:
        logger.error(f"处理订阅更新时发生错误: {e}", exc_info=True)
        raise


@queue_handler(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL)
def process_subscription_update_manual(message: Dict[str, Any]):
    try:
        _process_subscription_update(message, is_manual=True)
        return None
    except Exception as e:
        logger.error(f"处理手动订阅更新时发生错误: {e}", exc_info=True)
        raise

