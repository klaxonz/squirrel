import redis

from common.config import GlobalConfig
from redis.exceptions import LockError

class _RedisClient:
    def __init__(self, host='localhost', port=6379, db=0, decode_responses=True):
        self.connection_pool = redis.ConnectionPool(host=host, port=port, db=db, decode_responses=decode_responses)
        self.client = redis.Redis(connection_pool=self.connection_pool)
        self.client.ping()


# 实现单例
class RedisClient:
    _instance = None

    @staticmethod
    def get_instance():
        """
        获取RedisClient的单例实例，使用全局配置来初始化。
        """
        if RedisClient._instance is None:
            # 使用全局配置来初始化实例
            db = 0
            decode_responses = True
            host = GlobalConfig.get_redis_host()
            port = GlobalConfig.get_redis_port()
            RedisClient._instance = _RedisClient(host, port, db, decode_responses)
        return RedisClient._instance

    def get_client(self):
        """提供对内部Redis客户端的访问"""
        return self._instance.client


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
