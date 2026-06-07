import logging

import redis

from core.cache import create_redis_client

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client()
    return _redis_client


def publish_site_runtime_reload_signal() -> bool:
    try:
        client = get_redis_client()
        client.publish("squirrel:site-runtime:reload", "reload")
        logger.info("[redis] published site runtime reload signal")
        return True
    except Exception as e:
        # infrastructure boundary -- redis publish should not crash the caller
        logger.error("[redis] failed to publish site runtime reload signal: %s", e)
        return False
