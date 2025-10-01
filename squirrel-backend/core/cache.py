import logging

import redis
from redis import ConnectionPool
from redis_lock import Lock as RedisLock
from core.config import settings

logger = logging.getLogger()


_redis_pool = ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_DB,
    password=settings.REDIS_PASSWORD,
    decode_responses=True,
    max_connections=100,
    retry_on_timeout=True,
    socket_keepalive=True,
    socket_keepalive_options={},
    health_check_interval=30
)

redis_client = redis.Redis(connection_pool=_redis_pool)
logger.info("Redis client initialized")


def get_distributed_lock(
    lock_key: str,
    timeout: int = 180,
    auto_renewal: bool = True
) -> RedisLock:
    return RedisLock(
        redis_client,
        lock_key,
        expire=timeout,
        auto_renewal=auto_renewal,
        strict=True  # 严格模式：确保锁由当前线程持有
    )
