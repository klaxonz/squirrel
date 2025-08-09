import redis
from redis import ConnectionPool
from redis.exceptions import LockError

from core.config import settings


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
                max_connections=100,  # 增加连接池大小
                retry_on_timeout=True,
                socket_keepalive=True,
                socket_keepalive_options={},
                health_check_interval=30
            )
        self.client = redis.Redis(connection_pool=self._pool)

    def get_client(self):
        return self.client


class DistributedLock:
    def __init__(self, lock_key):
        self.redis_client = RedisClient.get_instance().client
        self.lock_key = lock_key
        self.lock = None

    def acquire(self, timeout=10, blocking_timeout=None):
        """尝试获取锁。timeout 为租约时长（秒），blocking_timeout 为等待时长（秒）。"""
        if blocking_timeout is None:
            blocking_timeout = timeout
        self.lock = self.redis_client.lock(self.lock_key, timeout=timeout)
        try:
            self.lock.acquire(blocking=True, blocking_timeout=blocking_timeout)
            return True
        except LockError:
            return False

    def is_locked(self) -> bool:
        """直接检查锁键是否存在。"""
        try:
            return bool(self.redis_client.exists(self.lock_key))
        except Exception:
            return False

    def extend(self, additional_time: int) -> bool:
        """在持有锁的情况下延长租约时间。"""
        try:
            if self.lock is not None and self.lock.locked():
                self.lock.extend(additional_time)
                return True
        except Exception:
            return False
        return False

    def release(self):
        """释放锁"""
        if self.lock is not None and self.lock.locked():
            self.lock.release()
