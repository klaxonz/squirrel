"""
订阅更新任务消费者
职责：接收订阅更新消息，调用编排器处理订阅更新
"""
import json
import logging
from typing import Dict, Any

from common import constants
from models.message import Message
from services.subscription_update.orchestrator import orchestrator
from services.subscription_update.models import SubscriptionUpdateRequest, UpdateTrigger, UpdateMode
from mq import mq_consumer

logger = logging.getLogger()


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_INCREMENTAL, group="subscription_update", consumer_name="subscription_update_incremental")
def process_subscription_update_incremental(message: Dict[str, Any]):
    """
    处理增量订阅更新消息（5分钟频率）
    职责：解析消息并调用编排器执行增量订阅更新
    """
    _process_subscription_update(message, UpdateTrigger.SCHEDULED)


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_FULL, group="subscription_update", consumer_name="subscription_update_full")
def process_subscription_update_full(message: Dict[str, Any]):
    """
    处理全量订阅更新消息（1小时频率）
    职责：解析消息并调用编排器执行全量订阅更新
    """
    _process_subscription_update(message, UpdateTrigger.SCHEDULED)


@mq_consumer(constants.QUEUE_SUBSCRIPTION_UPDATE_MANUAL, group="subscription_update", consumer_name="subscription_update_manual")
def process_subscription_update_manual(message: Dict[str, Any]):
    """
    处理手动订阅更新消息
    职责：解析消息并调用编排器执行订阅更新
    """
    _process_subscription_update(message, UpdateTrigger.MANUAL)


def process_domain_subscription_update(message: Dict[str, Any], queue_name: str):
    """
    处理域级别的订阅更新消息（用于域队列消费者）
    根据队列名判断是 manual、incremental 还是 full
    """
    if '::manual' in queue_name:
        trigger = UpdateTrigger.MANUAL
    else:
        trigger = UpdateTrigger.SCHEDULED
    _process_subscription_update(message, trigger)


def _process_subscription_update(message: Dict[str, Any], trigger: UpdateTrigger):
    """
    处理订阅更新消息的通用逻辑
    """
    try:
        message_obj = Message.from_dict(message)
        body_data = json.loads(message_obj.body)
        
        subscription_id = body_data.get('subscription_id')
        url = body_data.get('url')
        mode = body_data.get('mode', 'smart')
        user_id = body_data.get('user_id')
        force = body_data.get('force', False)
        trace_id = message_obj.trace_id if hasattr(message_obj, 'trace_id') else None
        
        if not subscription_id or not url:
            logger.error(f"Invalid message: missing subscription_id or url, message={body_data}")
            return
        
        logger.info(
            f"Processing subscription update: "
            f"id={subscription_id}, trigger={trigger.value}, mode={mode}, trace_id={trace_id}"
        )
        
        request = SubscriptionUpdateRequest(
            subscription_id=subscription_id,
            url=url,
            trigger=trigger,
            mode=UpdateMode(mode),
            user_id=user_id,
            force=force,
            trace_id=trace_id
        )
        
        result = orchestrator.update(request)
        
        if result.success:
            logger.info(
                f"Subscription update completed: id={subscription_id}, "
                f"found={result.videos_found}, enqueued={result.videos_enqueued}"
            )
        else:
            logger.error(
                f"Subscription update failed: id={subscription_id}, "
                f"error={result.error_message}"
            )
    
    except KeyError as e:
        logger.error(f"Invalid message format: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to process subscription update message: {e}", exc_info=True)
        raise

