import logging
from typing import Dict, Any
from datetime import datetime, timezone

from core.cache import RedisClient
from common import constants
from mq import mq_consumer
from mq.producer import RedisStreamProducer
from schemas.subscription.dto.subscription_update_dto import SubscriptionUpdateDto
from models.message import Message
from services import subscription_service
from services.subscription_update_service import SubscriptionUpdateService
from core.config import settings
from utils import url_helper

logger = logging.getLogger(__name__)
client = RedisClient.get_instance().get_client()


def _progress_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_UPDATE_PROGRESS_PREFIX}{sub_id}"


def _manual_flag_key(sub_id: int) -> str:
    return f"{constants.REDIS_KEY_SUBSCRIPTION_MANUAL_PENDING_PREFIX}{sub_id}"


def _clear_manual_flag(sub_id: int) -> None:
    client.delete(_manual_flag_key(sub_id))


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

    # scheduled 消费者尊重 manual_pending 标记，存在则跳过
    if not is_manual:
        if client.exists(_manual_flag_key(params.subscription_id)):
            logger.info(f"手动更新占用中，跳过定时更新: subscription_id={params.subscription_id}")
            return

    sub = subscription_service.get_subscription_detail(params.subscription_id)
    if not sub or getattr(sub, 'is_deleted', False):
        logger.info(f"订阅不存在或已删除: subscription_id={params.subscription_id}")
        return

    # manual 占用标记（短 TTL）
    if is_manual:
        client.set(_manual_flag_key(sub.id), 1, ex=120)

    # Ensure scheduled/manual enqueued flag exists and refresh TTL (48h)
    enq_flag = (
        f"{constants.REDIS_KEY_SUBSCRIPTION_ENQUEUED_MANUAL_PREFIX}{sub.id}" if is_manual
        else f"{constants.REDIS_KEY_SUBSCRIPTION_ENQUEUED_SCHEDULED_PREFIX}{sub.id}"
    )
    client.set(enq_flag, 1, ex=settings.SUB_ENQUEUED_TTL_SECONDS)

    try:
        SubscriptionUpdateService.update_subscription_videos(sub, is_manual=is_manual)
        sub_name = getattr(sub, 'name', f'subscription_{params.subscription_id}')
        logger.info(f"订阅更新消息已分发: {sub_name}, subscription_id={params.subscription_id}")
    except Exception as e:
        logger.error(f"订阅更新失败: subscription_id={params.subscription_id}, error={e}", exc_info=True)
        raise
    finally:
        # Clear enqueued flag on completion
        try:
            client.delete(enq_flag)
        except Exception:
            pass
        if is_manual:
            _clear_manual_flag(sub.id)


# Entry consumers: route by domain to site-specific queues
@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE, group="subscription", consumer_name="sub-update-entry")
def process_subscription_update_entry(message: Dict[str, Any]):
    try:
        message_obj = Message.from_dict(message)
        params = SubscriptionUpdateDto.model_validate_json(message_obj.body)

        # scheduled 入口尊重手动占用
        if client.exists(_manual_flag_key(params.subscription_id)):
            logger.info(f"手动更新占用中，跳过定时路由: subscription_id={params.subscription_id}")
            return

        # scheduled 入队去重
        enq_flag = f"{constants.REDIS_KEY_SUBSCRIPTION_ENQUEUED_SCHEDULED_PREFIX}{params.subscription_id}"
        if not client.set(enq_flag, 1, nx=True, ex=settings.SUB_ENQUEUED_TTL_SECONDS):
            return

        queue_name = _resolve_update_queue(params, is_manual=False)
        RedisStreamProducer().send(queue_name, message)
    except Exception as e:
        logger.error(f"路由订阅更新(定时)失败: {e}", exc_info=True)
        # 不抛出，避免阻断其他消息


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL, group="subscription", consumer_name="sub-update-manual-entry")
def process_subscription_update_entry_manual(message: Dict[str, Any]):
    try:
        message_obj = Message.from_dict(message)
        params = SubscriptionUpdateDto.model_validate_json(message_obj.body)

        # 手动占用标记（短 TTL），提升优先级
        client.set(_manual_flag_key(params.subscription_id), 1, ex=120)

        # manual 入队去重（不受 scheduled 标记影响）
        enq_flag = f"{constants.REDIS_KEY_SUBSCRIPTION_ENQUEUED_MANUAL_PREFIX}{params.subscription_id}"
        if not client.set(enq_flag, 1, nx=True, ex=settings.SUB_ENQUEUED_TTL_SECONDS):
            return

        queue_name = _resolve_update_queue(params, is_manual=True)
        RedisStreamProducer().send(queue_name, message)
    except Exception as e:
        logger.error(f"路由订阅更新(手动)失败: {e}", exc_info=True)


# Domain consumers: consume per-site queues and process
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

