import logging
from typing import Dict, Any
from pydantic import ValidationError

from common import constants
from mq import mq_consumer
from mq.message_router import subscription_update_router
from mq.consumer_registrar import DomainConsumerRegistrar
from mq.queue_config import QueueType
from schemas.subscription.dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService

logger = logging.getLogger()


def _parse_message(message: Dict[str, Any]) -> SubscriptionUpdateDto:
    """解析消息为 DTO"""
    try:
        # 从 Message 对象解析
        message_obj = Message.from_dict(message)
        return SubscriptionUpdateDto.model_validate_json(message_obj.body)
    except ValidationError as e:
        logger.error(f"Failed to parse message: {e}")
        raise


def _process_subscription_update(message: Dict[str, Any], is_manual: bool) -> None:
    source = "manual" if is_manual else "scheduled"
    params = _parse_message(message)
    
    logger.info(f"Processing subscription update ({source}): subscription_id={params.subscription_id}")

    sub = subscription_service.get_subscription_detail(params.subscription_id)
    if not sub or sub.is_deleted:
        logger.info(f"Subscription not found or deleted: subscription_id={params.subscription_id}")
        return
    
    try:
        SubscriptionUpdateService.update_subscription_videos(sub, is_manual=is_manual)
        logger.info(f"Subscription update completed: {sub.name}, subscription_id={params.subscription_id}")
    except Exception as e:
        logger.error(f"Subscription update failed: subscription_id={params.subscription_id}, error={e}", exc_info=True)
        raise


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE, group="subscription", consumer_name="sub-update-entry")
def process_subscription_update_entry(message: Dict[str, Any]) -> None:
    """处理定时订阅更新消息（入口队列）"""
    try:
        params = _parse_message(message)
        subscription_update_router.route(message, params.url, is_manual=False)
    except Exception as e:
        logger.error(f"Failed to route scheduled subscription update: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL, group="subscription", consumer_name="sub-update-manual-entry")
def process_subscription_update_entry_manual(message: Dict[str, Any]) -> None:
    """处理手动订阅更新消息（入口队列）"""
    try:
        params = _parse_message(message)
        subscription_update_router.route(message, params.url, is_manual=True)
    except Exception as e:
        logger.error(f"Failed to route manual subscription update: {e}", exc_info=True)


# 域队列消费者工厂
def _create_domain_handler(queue_name: str):
    """创建域队列处理函数（闭包工厂）"""
    is_manual = 'manual' in queue_name
    
    def handler(message: Dict[str, Any]) -> None:
        try:
            _process_subscription_update(message, is_manual=is_manual)
        except Exception as e:
            logger.error(f"Error processing subscription update: {e}", exc_info=True)
            raise
    
    return handler


def _register_domain_consumers():
    """
    动态注册所有域队列消费者
    
    基于插件注册表自动识别支持的站点，完全消除硬编码
    新增站点只需注册插件即可，无需修改任何配置
    """
    count = DomainConsumerRegistrar.register_with_stream_param(
        queue_type=QueueType.SUBSCRIPTION_UPDATE,
        group='subscription-domain',
        consumer_prefix='sub-update',
        handler_factory=_create_domain_handler,
        block_ms=1000,
        read_count=1
    )
    logger.info(f"Subscription update: registered {count} domain consumers")


# 模块加载时自动注册
# 注意：此代码在模块被导入时执行，由 mq/runner.py 的 module_discovery 触发
_register_domain_consumers()

