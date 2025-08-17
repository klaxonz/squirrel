import logging
import threading
from typing import Optional
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
    def __init__(
        self,
        lock_key: str,
        timeout: int = 10,
        blocking_timeout: Optional[int] = None,
        auto_renew: bool = True,
        renew_interval: int = 60,
        renew_extend: int = 120,
    ):
        self.redis_client = RedisClient.get_instance().client
        self.lock_key = lock_key
        self.lock = None
        self._logger = logging.getLogger(__name__)
        self._renew_thread: Optional[threading.Thread] = None
        self._renew_stop: Optional[threading.Event] = None
        # context manager configs
        self._timeout = timeout
        self._blocking_timeout = blocking_timeout
        self._auto_renew_enabled = auto_renew
        self._renew_interval = renew_interval
        self._renew_extend = renew_extend

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

    # 方便 with 语法使用
    def __enter__(self):
        ok = self.acquire(timeout=self._timeout, blocking_timeout=self._blocking_timeout)
        if not ok:
            raise LockError(f"Failed to acquire lock: {self.lock_key}")
        if self._auto_renew_enabled:
            self.auto_renew_start(interval_seconds=self._renew_interval, extend_seconds=self._renew_extend)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.release()
        # 不吞掉异常
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

    def auto_renew_start(self, interval_seconds: int = 60, extend_seconds: int = 120) -> None:
        """启动自动续期线程。在持有锁的情况下每隔 interval_seconds 延长 extend_seconds。"""
        if self.lock is None or not self.lock.locked():
            return
        if self._renew_thread is not None:
            return
        self._renew_stop = threading.Event()

        def _renew_loop():
            assert self._renew_stop is not None
            while not self._renew_stop.wait(interval_seconds):
                try:
                    ok = self.extend(extend_seconds)
                    if not ok:
                        self._logger.warning(f"Failed to extend lock lease for {self.lock_key}")
                except Exception as e:
                    self._logger.error(f"Error extending lock lease for {self.lock_key}: {e}", exc_info=True)

        self._renew_thread = threading.Thread(target=_renew_loop, name=f"lock-renew-{self.lock_key}", daemon=True)
        self._renew_thread.start()

    def auto_renew_stop(self) -> None:
        """停止自动续期线程。"""
        if self._renew_stop is not None:
            self._renew_stop.set()
        if self._renew_thread is not None:
            try:
                self._renew_thread.join(timeout=2)
            except Exception:
                pass
        self._renew_thread = None
        self._renew_stop = None

    def release(self):
        """释放锁"""
        # 先停止续期
        self.auto_renew_stop()
        if self.lock is not None and self.lock.locked():
            self.lock.release()
