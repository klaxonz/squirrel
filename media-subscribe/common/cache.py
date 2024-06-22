import redis

from common.config import GlobalConfig


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
