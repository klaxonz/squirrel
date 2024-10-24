from dramatiq.brokers.redis import RedisBroker
from core.config import settings
import dramatiq
redis_broker = RedisBroker(url=settings.get_redis_url())
dramatiq.set_broker(broker=redis_broker)