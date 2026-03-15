import logging
from typing import Optional

import redis

from core.cache import create_redis_client

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client()
    return _redis_client


def publish_plugin_reload_signal() -> bool:
    try:
        client = get_redis_client()
        client.publish("squirrel:plugin:reload", "reload")
        logger.info("[redis] published plugin reload signal")
        return True
    except Exception as e:
        logger.error("[redis] failed to publish plugin reload signal: %s", e)
        return False
