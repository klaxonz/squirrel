from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import TimeLimit, CurrentMessage

from core.config import settings

redis_broker = RedisBroker(url=settings.get_redis_url())
redis_broker.middleware = [TimeLimit(), CurrentMessage()]
