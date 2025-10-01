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


def _parse_message(message: Dict[str, Any]) -> SubscriptionUpdateDto:
    message_obj = Message.from_dict(message)
    return SubscriptionUpdateDto.model_validate_json(message_obj.body)


def _resolve_domain_queue(url: str, is_manual: bool) -> str:
    domain = url_helper.extract_top_level_domain(url)
    mapping = constants.SUBSCRIPTION_UPDATE_DOMAIN_QUEUE_MAPPING.get(domain)
    if not mapping:
        raise ValueError(f"Unsupported domain for subscription update: {domain}")
    
    queue_name = mapping.get('manual' if is_manual else 'scheduled')
    if not queue_name:
        raise ValueError(f"No queue mapping for domain {domain}")
    return queue_name


def _route_to_domain_queue(message: Dict[str, Any], is_manual: bool) -> None:
    params = _parse_message(message)
    queue_name = _resolve_domain_queue(params.url, is_manual)
    RedisStreamProducer().send(queue_name, message)


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
    try:
        _route_to_domain_queue(message, is_manual=False)
    except Exception as e:
        logger.error(f"Failed to route scheduled subscription update: {e}", exc_info=True)


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL, group="subscription", consumer_name="sub-update-manual-entry")
def process_subscription_update_entry_manual(message: Dict[str, Any]) -> None:
    try:
        _route_to_domain_queue(message, is_manual=True)
    except Exception as e:
        logger.error(f"Failed to route manual subscription update: {e}", exc_info=True)


def _register_domain_consumers():
    for domain, site_name in constants.SUPPORTED_SITES.items():
        for mode in ['manual', 'scheduled']:
            queue_name = f'queue::subscription::update::{site_name}::{mode}'
            mq_consumer(
                queue_name, 
                group="subscription-domain", 
                consumer_name="sub-update-domain"
            )(process_subscription_update_domain)


@mq_consumer("queue::subscription::update::bilibili::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::bilibili::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::youtube::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::youtube::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::pornhub::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::pornhub::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::javdb::manual", group="subscription-domain", consumer_name="sub-update-domain")
@mq_consumer("queue::subscription::update::javdb::scheduled", group="subscription-domain", consumer_name="sub-update-domain")
def process_subscription_update_domain(message: Dict[str, Any], stream: str) -> None:
    try:
        is_manual = 'manual' in stream
        _process_subscription_update(message, is_manual=is_manual)
    except Exception as e:
        logger.error(f"Error processing subscription update: {e}", exc_info=True)
        raise

