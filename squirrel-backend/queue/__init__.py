"""业务无关的 MQ 基础设施（Redis Streams）。

包括：消息模型、生产者、消费者、注册表、装饰器与运行器。
业务处理逻辑请放在 processors 下，并通过装饰器进行注册。
"""

from .message import MqMessage
from .producer import RedisStreamProducer
from .consumer import RedisStreamConsumer, ConsumerOptions
from .registry import ConsumerRegistry, ConsumerSpec
from .decorators import queue_listener
from .message_router import MessageRouter
from .consumer_registrar import DomainConsumerRegistrar
from .duplicate_checker import MessageDuplicateChecker, create_checker, create_simple_checker
from .direct_producer import DirectDomainProducer, direct_domain_producer
from .queue_config import (
    QueueConfigManager,
    get_queue_config,
    ensure_queue_config_initialized,
    QueueType,
    QueueMode
)

__all__ = [
    "MqMessage",
    "RedisStreamProducer",
    "RedisStreamConsumer",
    "ConsumerOptions",
    "ConsumerRegistry",
    "ConsumerSpec",
    "queue_listener",
    "MessageRouter",
    "DomainConsumerRegistrar",
    "MessageDuplicateChecker",
    "create_checker",
    "create_simple_checker",
    "DirectDomainProducer",
    "direct_domain_producer",
    "QueueConfigManager",
    "get_queue_config",
    "ensure_queue_config_initialized",
    "QueueType",
    "QueueMode",
]


