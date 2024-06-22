import redis

class _RedisClient:
    def __init__(self, host='localhost', port=6379, db=0, decode_responses=True):
        try:
            self.connection_pool = redis.ConnectionPool(host=host, port=port, db=db, decode_responses=decode_responses)
            self.client = redis.Redis(connection_pool=self.connection_pool)
            self.client.ping()
        except redis.exceptions.ConnectionError as e:
            print(f"无法连接到Redis服务器: {e}")

    def set_value(self, key, value):
        return self.client.set(key, value)

    def get_value(self, key):
        return self.client.get(key)

    def delete_key(self, key):
        return self.client.delete(key)

    def hset(self, key, field, value):
        return self.client.hset(key, field, value)

# 实现单例
class RedisClient:
    _instance = None

    @staticmethod
    def get_instance(host='localhost', port=6379, db=0, decode_responses=True):
        if RedisClient._instance is None:
            RedisClient._instance = _RedisClient(host, port, db, decode_responses)
        return RedisClient._instance


