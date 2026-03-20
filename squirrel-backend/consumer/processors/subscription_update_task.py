"""
订阅更新任务消费者
职责：接收域队列的订阅更新消息，调用编排器处理订阅更新
"""
import json
import logging
from typing import Dict, Any

from models.message import Message
from services import subscription_service, subscription_sync_state_service
from services.subscription_update.orchestrator import orchestrator
from services.subscription_update.models import SubscriptionUpdateRequest, UpdateTrigger, UpdateMode

logger = logging.getLogger()


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
        sync_state_id = body_data.get('sync_state_id')
        mode = body_data.get('mode', 'incremental')
        user_id = body_data.get('user_id')
        force = body_data.get('force', False)
        queue_token = body_data.get('queue_token')
        trace_id = message_obj.trace_id if hasattr(message_obj, 'trace_id') else None
        
        if not subscription_id or not sync_state_id or not queue_token:
            logger.error(f"Invalid message: missing subscription_id or sync state, message={body_data}")
            return

        claimed_state = subscription_sync_state_service.claim_sync_state(sync_state_id, queue_token)
        if not claimed_state:
            logger.debug(
                f"Skip subscription update because state can not be claimed: "
                f"subscription_id={subscription_id}, sync_state_id={sync_state_id}"
            )
            return

        subscription = subscription_service.get_subscription_by_id(subscription_id)
        if not subscription or not subscription.url:
            subscription_sync_state_service.mark_sync_failed(sync_state_id, 'subscription_not_found')
            logger.error(f"Subscription not found while processing sync state: subscription_id={subscription_id}")
            return
        
        logger.debug(
            f"Processing subscription update: "
            f"id={subscription_id}, trigger={trigger.value}, mode={mode}, sync_state_id={sync_state_id}, trace_id={trace_id}"
        )
        
        request = SubscriptionUpdateRequest(
            subscription_id=subscription_id,
            url=subscription.url,
            trigger=trigger,
            mode=UpdateMode(mode),
            user_id=user_id,
            force=force,
            trace_id=trace_id,
            sync_state_id=sync_state_id,
            queue_token=queue_token,
            cursor_payload=claimed_state.cursor_payload or {},
            last_seen_video_url=claimed_state.last_seen_video_url,
        )

        result = orchestrator.update(request)
        
        if result.success:
            if result.skipped_reason:
                logger.debug(f"Subscription update skipped: id={subscription_id}, reason={result.skipped_reason}")
            else:
                logger.debug(
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

