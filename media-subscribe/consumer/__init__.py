from consumer.base import redis_broker
import dramatiq

dramatiq.set_broker(redis_broker)
