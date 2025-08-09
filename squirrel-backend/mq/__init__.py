"""业务无关的 MQ 基础设施（Redis Streams）。

包括：消息模型、生产者、消费者、注册表、装饰器与运行器。
业务处理逻辑请放在 processors 下，并通过装饰器进行注册。
"""

from .message import MqMessage
from .producer import RedisStreamProducer
from .consumer import RedisStreamConsumer, ConsumerOptions
from .registry import ConsumerRegistry, ConsumerSpec
from .decorators import mq_consumer

__all__ = [
    "MqMessage",
    "RedisStreamProducer",
    "RedisStreamConsumer",
    "ConsumerOptions",
    "ConsumerRegistry",
    "ConsumerSpec",
    "mq_consumer",
]


