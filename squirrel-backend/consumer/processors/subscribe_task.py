"""订阅任务消费者
职责：接收订阅消息，调度到服务层处理
"""
import json
import logging
from typing import Any

from common import constants
from models.message import Message
from queues import queue_listener
from services import subscription_service
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger(__name__)


@queue_listener(constants.QUEUE_SUBSCRIBE, group="subscription", consumer_name="subscribe")
def process_subscribe_message(message: dict[str, Any]):
    """处理订阅消息
    职责：解析消息并调度到服务层
    """
    try:
        message_obj = Message.from_dict(message)
        body_data = json.loads(message_obj.body)
        url = body_data.get("url")
        user_id = body_data.get("user_id")

        if not url or not user_id:
            logger.error("Invalid message: missing url or user_id, message=%s", body_data)
            return

        domain = extract_top_level_domain(url)
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info("Skip subscribe request because site is disabled: url=%s, user_id=%s", url, user_id)
            return

        logger.info("Processing subscribe request: url=%s, user_id=%s", url, user_id)

        subscription = subscription_service.handle_subscribe_request(url, user_id)

        logger.info("Subscribe completed: %s (id=%s)", subscription.name, subscription.id)

    except KeyError as e:
        logger.error("Invalid message format: %s", e, exc_info=True)
    except Exception as e:  # consumer boundary -- prevent single message from crashing consumer
        logger.error("Failed to process subscribe message: %s", e, exc_info=True)
        raise

