import logging
from typing import Dict, Any, Iterable, cast

from common import constants
from dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService
from consumer.queue_management.decorators import queue_handler
from consumer.queue_management.manager import QueueManager

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


@queue_handler("subscription_update_batch")
def process_batch_subscription_update(message: Dict[str, Any]):
    try:
        subscription_ids = message['subscription_ids']
        batch_id = message.get('batch_id', 'unknown')

        logger.info(f"开始批量订阅更新: batch_id={batch_id}, 订阅数={len(subscription_ids)}")

        results = []
        for subscription_id in subscription_ids:
            try:
                update_dto = SubscriptionUpdateDto(
                    subscription_id=subscription_id,
                    url="",
                    total_videos=0,
                    total_extract=0
                )
                update_message = {
                    "body": update_dto.model_dump_json()
                }

                QueueManager.send_message(constants.QUEUE_SUBSCRIPTION_UPDATE, update_message)
                results.append({"subscription_id": subscription_id, "status": "queued"})

            except Exception as e:
                logger.error(f"批量更新中单个订阅失败: subscription_id={subscription_id}, error={e}")
                results.append({"subscription_id": subscription_id, "status": "failed", "error": str(e)})

        success_count = len([r for r in results if r['status'] == 'queued'])
        logger.info(f"批量订阅更新完成: batch_id={batch_id}, 成功={success_count}/{len(subscription_ids)}")

        return None

    except Exception as e:
        logger.error(f"批量订阅更新失败: {e}", exc_info=True)
        raise


@queue_handler("subscription_update_priority_*")
def process_priority_subscription_update(message: Dict[str, Any], queue_name: str):
    priority = 'normal'
    try:
        priority = queue_name.split('_')[-1] if '_' in queue_name else 'normal'

        logger.info(f"开始处理优先级订阅更新: priority={priority}")

        if priority == 'high':
            timeout = 300  # 5分钟
            max_videos = 100  # 最多处理100个视频
        elif priority == 'urgent':
            timeout = 180  # 3分钟
            max_videos = 50   # 最多处理50个视频
        else:
            timeout = 600  # 10分钟
            max_videos = 200  # 最多处理200个视频

        message['_priority'] = priority
        message['_timeout'] = timeout
        message['_max_videos'] = max_videos

        process_subscription_update(message)

        logger.info(f"优先级订阅更新完成: priority={priority}")
        return None

    except Exception as e:
        logger.error(f"优先级订阅更新失败: priority={priority}, error={e}", exc_info=True)
        raise


@queue_handler("subscription_update_scheduled")
def process_scheduled_subscription_update(message: Dict[str, Any]):
    try:
        logger.info("开始定时订阅更新")

        getter = getattr(subscription_service, 'get_all_active_subscriptions', None)
        if callable(getter):
            _subs = getter()
            if isinstance(_subs, list):
                active_subscriptions = _subs
            elif hasattr(_subs, '__iter__'):
                active_subscriptions = list(cast(Iterable, _subs))
            else:
                active_subscriptions = []
        else:
            logger.warning("get_all_active_subscriptions method not found, using alternative")
            active_subscriptions = []

        if not active_subscriptions:
            logger.info("没有找到活跃的订阅")
            return None

        logger.info(f"找到 {len(active_subscriptions)} 个活跃订阅")

        batch_message = {
            "subscription_ids": [sub.id for sub in active_subscriptions],
            "batch_id": f"scheduled_{message.get('timestamp', 'unknown')}"
        }

        QueueManager.send_message("subscription_update_batch", batch_message)

        logger.info(f"定时订阅更新任务已发送: {len(active_subscriptions)} 个订阅")

        return None

    except Exception as e:
        logger.error(f"定时订阅更新失败: {e}", exc_info=True)
        raise

