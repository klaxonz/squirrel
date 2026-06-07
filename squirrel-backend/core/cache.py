import logging
from typing import Any

import redis
from redis import BlockingConnectionPool
from redis_lock import Lock as RedisLock

from core.config import settings

logger = logging.getLogger(__name__)


def get_redis_connection_kwargs() -> dict[str, Any]:
    return {
        "host": settings.REDIS_HOST,
        "port": settings.REDIS_PORT,
        "db": settings.REDIS_DB,
        "password": settings.REDIS_PASSWORD or None,
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
    return BlockingConnectionPool(
        max_connections=max_connections or settings.REDIS_MAX_CONNECTIONS,
        timeout=timeout or settings.REDIS_POOL_TIMEOUT,
        **get_redis_connection_kwargs(),
    )


def create_redis_client(*, connection_pool: BlockingConnectionPool | None = None) -> redis.Redis:
    return redis.Redis(connection_pool=connection_pool or create_redis_pool())


_redis_pool = create_redis_pool()
redis_client = create_redis_client(connection_pool=_redis_pool)
logger.info("Redis client initialized")


def set_redis_client(client: redis.Redis) -> None:
    global redis_client
    redis_client = client


def get_distributed_lock(
    lock_key: str,
    timeout: int = 180,
    auto_renewal: bool = True,
) -> RedisLock:
    return RedisLock(
        redis_client,
        lock_key,
        expire=timeout,
        auto_renewal=auto_renewal,
        strict=True,  # 严格模式：确保锁由当前线程持有
    )
