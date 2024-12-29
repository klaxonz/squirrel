import redis
from core.config import settings
from redis import ConnectionPool
from redis.exceptions import LockError


class RedisClient:
    _instance = None
    _pool = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if self._pool is None:
            self._pool = ConnectionPool(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD,
                decode_responses=True,
                max_connections=20
            )
        self.client = redis.Redis(connection_pool=self._pool)

    def get_client(self):
        return self.client


class DistributedLock:
    def __init__(self, lock_key):
        self.redis_client = RedisClient.get_instance().client
        self.lock_key = lock_key
        self.lock = None

    def acquire(self, timeout=10):
        """尝试获取锁，超时则放弃"""
        self.lock = self.redis_client.lock(self.lock_key, timeout=timeout)
        try:
            self.lock.acquire(blocking=True, blocking_timeout=timeout)
            return True
        except LockError:
            return False

    def release(self):
        """释放锁"""
        if self.lock is not None and self.lock.locked():
            self.lock.release()
