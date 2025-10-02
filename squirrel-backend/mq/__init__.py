"""业务无关的 MQ 基础设施（Redis Streams）。

包括：消息模型、生产者、消费者、注册表、装饰器与运行器。
业务处理逻辑请放在 processors 下，并通过装饰器进行注册。
"""

from .message import MqMessage
from .producer import RedisStreamProducer
from .consumer import RedisStreamConsumer, ConsumerOptions
from .registry import ConsumerRegistry, ConsumerSpec
from .decorators import mq_consumer
from .message_router import MessageRouter, video_extract_router, subscription_update_router
from .consumer_registrar import DomainConsumerRegistrar
from .duplicate_checker import MessageDuplicateChecker, create_checker, create_simple_checker
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
    "mq_consumer",
    "MessageRouter",
    "video_extract_router",
    "subscription_update_router",
    "DomainConsumerRegistrar",
    "MessageDuplicateChecker",
    "create_checker",
    "create_simple_checker",
    "QueueConfigManager",
    "get_queue_config",
    "ensure_queue_config_initialized",
    "QueueType",
    "QueueMode",
]


