import dramatiq
from core.config import settings
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, TimeLimit, ShutdownNotifications, Callbacks, Pipelines, Retries

broker_middleware = [
    AgeLimit, TimeLimit,
    ShutdownNotifications, Callbacks, Pipelines, Retries
]
broker_middleware = [m() for m in broker_middleware]

redis_broker = RedisBroker(url=settings.get_redis_url(), middleware=broker_middleware)
dramatiq.set_broker(broker=redis_broker)
