from typing import Type

from consumer.base import BaseConsumerThread


class ConsumerRegistry:
    consumers = {}

    @classmethod
    def register(cls, queue_name: str, num_threads: int = 1):
        def decorator(consumer_class: Type[BaseConsumerThread]):
            cls.consumers[queue_name] = {
                'class': consumer_class,
                'num_threads': num_threads
            }
            return consumer_class
        return decorator

    @classmethod
    def get_consumers(cls):
        return cls.consumers