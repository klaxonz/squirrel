"""
消费者注册器

基于插件注册表动态注册消费者，完全消除硬编码
"""
import logging
from typing import Callable, Dict, Any
from mq.registry import ConsumerRegistry
from mq.queue_config import get_queue_config, QueueType, QueueMode

logger = logging.getLogger()


class DomainConsumerRegistrar:
    """域队列消费者注册器 - 基于插件注册表动态注册"""
    
    @staticmethod
    def register_all(
        queue_type: QueueType,
        group: str,
        consumer_prefix: str,
        handler: Callable[[Dict[str, Any]], None],
        block_ms: int = 1000,
        read_count: int = 1
    ) -> int:
        """
        为所有支持的站点注册域队列消费者
        
        Args:
            queue_type: 队列类型枚举
            group: 消费者组名
            consumer_prefix: 消费者名称前缀
            handler: 消息处理函数
            block_ms: 阻塞时间（毫秒）
            read_count: 每次读取消息数量
            
        Returns:
            注册的消费者数量
        """
        config = get_queue_config()
        registered_count = 0
        
        # 根据队列类型选择对应的模式
        if queue_type == QueueType.SUBSCRIPTION_UPDATE:
            modes = [QueueMode.MANUAL, QueueMode.INCREMENTAL, QueueMode.FULL]
        else:
            modes = [QueueMode.MANUAL, QueueMode.SCHEDULED]
        
        for site in config.get_supported_sites():
            for mode in modes:
                queue_name = config.build_queue_name(queue_type, site, mode)
                consumer_name = f"{consumer_prefix}-{site}-{mode.value}"
                
                try:
                    ConsumerRegistry.register(
                        stream=queue_name,
                        group=group,
                        consumer_name=consumer_name,
                        handler=handler,
                        block_ms=block_ms,
                        read_count=read_count
                    )
                    registered_count += 1
                    logger.debug(f"Registered consumer: {consumer_name} for {queue_name}")
                except Exception as e:
                    logger.error(f"Failed to register consumer for {queue_name}: {e}")
        
        return registered_count
    
    @staticmethod
    def register_with_stream_param(
        queue_type: QueueType,
        group: str,
        consumer_prefix: str,
        handler_factory: Callable[[str], Callable[[Dict[str, Any]], None]],
        block_ms: int = 1000,
        read_count: int = 1
    ) -> int:
        """
        注册需要 stream 参数的消费者（使用工厂函数）
        
        Args:
            queue_type: 队列类型枚举
            group: 消费者组名
            consumer_prefix: 消费者名称前缀
            handler_factory: 接收 queue_name 返回 handler 的工厂函数
            block_ms: 阻塞时间
            read_count: 每次读取消息数量
            
        Returns:
            注册的消费者数量
        """
        config = get_queue_config()
        registered_count = 0
        
        # 根据队列类型选择对应的模式
        if queue_type == QueueType.SUBSCRIPTION_UPDATE:
            modes = [QueueMode.MANUAL, QueueMode.INCREMENTAL, QueueMode.FULL]
        else:
            modes = [QueueMode.MANUAL, QueueMode.SCHEDULED]
        
        for site in config.get_supported_sites():
            for mode in modes:
                queue_name = config.build_queue_name(queue_type, site, mode)
                consumer_name = f"{consumer_prefix}-{site}-{mode.value}"
                
                try:
                    handler = handler_factory(queue_name)
                    ConsumerRegistry.register(
                        stream=queue_name,
                        group=group,
                        consumer_name=consumer_name,
                        handler=handler,
                        block_ms=block_ms,
                        read_count=read_count
                    )
                    registered_count += 1
                    logger.debug(f"Registered consumer: {consumer_name} for {queue_name}")
                except Exception as e:
                    logger.error(f"Failed to register consumer for {queue_name}: {e}")
        
        return registered_count

