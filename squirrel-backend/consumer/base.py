from core.config import settings
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import TimeLimit, CurrentMessage

# 创建 broker 实例
redis_broker = RedisBroker(url=settings.get_redis_url())

# 添加中间件
redis_broker.middleware = [TimeLimit(), CurrentMessage()]

# 导出 broker
__all__ = ['redis_broker']