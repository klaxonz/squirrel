"""
订阅任务消费者
职责：接收订阅消息，调度到服务层处理
"""
import json
import logging
from typing import Dict, Any

from common import constants
from models.message import Message
from services import subscription_service
from mq import mq_consumer
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger()


@mq_consumer(constants.QUEUE_SUBSCRIBE, group="subscription", consumer_name="subscribe")
def process_subscribe_message(message: Dict[str, Any]):
    """
    处理订阅消息
    职责：解析消息并调度到服务层
    """
    try:
        message_obj = Message.from_dict(message)
        body_data = json.loads(message_obj.body)
        url = body_data.get('url')
        user_id = body_data.get('user_id')
        
        if not url or not user_id:
            logger.error(f"Invalid message: missing url or user_id, message={body_data}")
            return

        domain = extract_top_level_domain(url)
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info(f"Skip subscribe request because site is disabled: url={url}, user_id={user_id}")
            return
        
        logger.info(f"Processing subscribe request: url={url}, user_id={user_id}")

        subscription = subscription_service.handle_subscribe_request(url, user_id)
        
        logger.info(f"Subscribe completed: {subscription.name} (id={subscription.id})")

    except KeyError as e:
        logger.error(f"Invalid message format: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to process subscribe message: {e}", exc_info=True)

