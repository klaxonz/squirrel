import logging
import redis
from typing import Optional

from core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
        )
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
