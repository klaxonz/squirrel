import dramatiq
from consumer.base import redis_broker

dramatiq.set_broker(redis_broker)
