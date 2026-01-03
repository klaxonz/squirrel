"""
消费者配置管理器
集中管理消费者注册的配置，避免硬编码分散在各处
"""
import logging
from dataclasses import dataclass
from typing import Callable, Dict, Any
from queues.queue_config import QueueType

logger = logging.getLogger()


@dataclass
class ConsumerConfig:
    """消费者配置"""
    queue_type: QueueType
    group: str
    consumer_prefix: str
    handler: Callable[[Dict[str, Any]], None]
    block_ms: int = 1000
    read_count: int = 1


class ConsumerConfigManager:
    """消费者配置管理器"""
    
    _configs: Dict[QueueType, ConsumerConfig] = {}
    
    @classmethod
    def register_config(cls, config: ConsumerConfig):
        """注册配置"""
        cls._configs[config.queue_type] = config
    
    @classmethod
    def get_config(cls, queue_type: QueueType) -> ConsumerConfig:
        """获取配置"""
        if queue_type not in cls._configs:
            raise ValueError(f"No config registered for queue_type: {queue_type}")
        return cls._configs[queue_type]
    
    @classmethod
    def register_all_domain_consumers(cls) -> int:
        """
        注册所有已配置的域消费者
        
        Returns:
            总共注册的消费者数量
        """
        from queues.consumer_registrar import DomainConsumerRegistrar
        
        total_count = 0
        
        for queue_type, config in cls._configs.items():
            count = DomainConsumerRegistrar.register_all(
                queue_type=config.queue_type,
                group=config.group,
                consumer_prefix=config.consumer_prefix,
                handler=config.handler,
                block_ms=config.block_ms,
                read_count=config.read_count
            )
            logger.info(f"{queue_type.name}: registered {count} domain consumers")
            total_count += count
        
        return total_count


def init_domain_consumers():
    """
    初始化所有域消费者
    应在应用启动时调用
    """
    total = ConsumerConfigManager.register_all_domain_consumers()
    logger.info(f"Total domain consumers registered: {total}")

