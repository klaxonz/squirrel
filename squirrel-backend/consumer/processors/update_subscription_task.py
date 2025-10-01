import logging
from typing import Dict, Any
from common import constants
from mq import mq_consumer
from mq.producer import RedisStreamProducer
from schemas.subscription.dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService
from utils import url_helper

logger = logging.getLogger()


def _resolve_update_queue(params: SubscriptionUpdateDto, is_manual: bool) -> str:
    domain = url_helper.extract_top_level_domain(params.url)
    mapping = constants.SUBSCRIPTION_UPDATE_DOMAIN_QUEUE_MAPPING.get(domain)
    if not mapping:
        raise ValueError(f"Unsupported domain for subscription update: {domain}")
    queue_name = mapping.get('manual' if is_manual else 'scheduled')
    if not queue_name:
        raise ValueError(f"No queue mapping for domain {domain} and source {'manual' if is_manual else 'scheduled'}")
    return queue_name


def _process_subscription_update(message: Dict[str, Any], is_manual: bool) -> None:
    source = "manual" if is_manual else "scheduled"
    logger.info(f"开始处理订阅更新消息({source}): {message}")
    message_obj = Message.from_dict(message)
    params = SubscriptionUpdateDto.model_validate_json(message_obj.body)

    sub = subscription_service.get_subscription_detail(params.subscription_id)
    if not sub or getattr(sub, 'is_deleted', False):
        logger.info(f"订阅不存在或已删除: subscription_id={params.subscription_id}")
        return
    try:
        SubscriptionUpdateService.update_subscription_videos(sub, is_manual=is_manual)
        sub_name = getattr(sub, 'name', f'subscription_{params.subscription_id}')
        logger.info(f"订阅更新消息已分发: {sub_name}, subscription_id={params.subscription_id}")
    except Exception as e:
        logger.error(f"订阅更新失败: subscription_id={params.subscription_id}, error={e}", exc_info=True)
        raise


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE, group="subscription", consumer_name="sub-update-entry")
def process_subscription_update_entry(message: Dict[str, Any]):
    try:
        message_obj = Message.from_dict(message)
        params = SubscriptionUpdateDto.model_validate_json(message_obj.body)

        queue_name = _resolve_update_queue(params, is_manual=False)
        RedisStreamProducer().send(queue_name, message)
    except Exception as e:
        logger.error(f"路由订阅更新(定时)失败: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL, group="subscription", consumer_name="sub-update-manual-entry")
def process_subscription_update_entry_manual(message: Dict[str, Any]):
    try:
        message_obj = Message.from_dict(message)
        params = SubscriptionUpdateDto.model_validate_json(message_obj.body)
        queue_name = _resolve_update_queue(params, is_manual=True)
        RedisStreamProducer().send(queue_name, message)
    except Exception as e:
        logger.error(f"路由订阅更新(手动)失败: {e}", exc_info=True)


@mq_consumer("queue::subscription::update::bilibili::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::bilibili::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::youtube::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::youtube::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::pornhub::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::pornhub::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::javdb::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::javdb::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
def process_subscription_update_domain(message: Dict[str, Any], stream: str):
    try:
        is_manual = 'manual' in stream
        _process_subscription_update(message, is_manual=is_manual)
    except Exception as e:
        logger.error(f"处理订阅更新(域)时发生错误: {e}", exc_info=True)
        raise

