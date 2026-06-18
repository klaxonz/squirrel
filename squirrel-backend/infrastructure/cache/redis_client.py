import logging
from typing import Any

import redis
from redis import BlockingConnectionPool

from infrastructure.config.settings import settings

logger = logging.getLogger(__name__)


def get_redis_connection_kwargs() -> dict[str, Any]:
    redis_cfg = settings.redis
    return {
        "host": redis_cfg.host,
        "port": redis_cfg.port,
        "db": redis_cfg.db,
        "password": redis_cfg.password or None,
        "decode_responses": True,
        "retry_on_timeout": True,
        "socket_keepalive": True,
        "socket_keepalive_options": {},
        "socket_connect_timeout": 5,
        "health_check_interval": 30,
    }


def create_redis_pool(
    *,
    max_connections: int | None = None,
    timeout: int | None = None,
) -> BlockingConnectionPool:
    redis_cfg = settings.redis
    return BlockingConnectionPool(
        max_connections=max_connections or redis_cfg.max_connections,
        timeout=timeout or redis_cfg.pool_timeout,
        **get_redis_connection_kwargs(),
    )


def create_redis_client(*, connection_pool: BlockingConnectionPool | None = None) -> redis.Redis:
    return redis.Redis(connection_pool=connection_pool or create_redis_pool())


_redis_pool = create_redis_pool()
redis_client = create_redis_client(connection_pool=_redis_pool)
logger.info("Redis client initialized")
