"""Site-runtime domain signals.

Publishes reload notifications over Redis pub/sub so other processes that host
site runtimes can pick up configuration/cookie changes.
"""
import logging

from infrastructure.cache.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def publish_site_runtime_reload_signal() -> bool:
    """Notify all site-runtime hosts to reload.

    Returns:
        True if the signal was published, False on infrastructure failure.
    """
    try:
        client = get_redis_client()
        client.publish("squirrel:site-runtime:reload", "reload")
        logger.info("[redis] published site runtime reload signal")
        return True
    except Exception as e:
        # infrastructure boundary -- redis publish should not crash the caller
        logger.error("[redis] failed to publish site runtime reload signal: %s", e)
        return False
