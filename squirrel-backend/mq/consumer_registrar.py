"""
消费者注册器

提供统一的动态消费者注册功能，避免硬编码队列名称
"""
import logging
from typing import Callable, Dict, Any
from common import constants
from mq.registry import ConsumerRegistry

logger = logging.getLogger()


class DomainConsumerRegistrar:
    """域队列消费者注册器"""
    
    @staticmethod
    def register_all(
        queue_template: str,
        group: str,
        consumer_prefix: str,
        handler: Callable[[Dict[str, Any]], None],
        block_ms: int = 1000,
        read_count: int = 1
    ) -> int:
        """
        为所有支持的站点注册域队列消费者
        
        Args:
            queue_template: 队列名称模板，如 'queue::video::extract::{site}::{mode}'
            group: 消费者组名
            consumer_prefix: 消费者名称前缀
            handler: 消息处理函数
            block_ms: 阻塞时间（毫秒）
            read_count: 每次读取消息数量
            
        Returns:
            注册的消费者数量
        """
        registered_count = 0
        
        for site_name in constants.SUPPORTED_SITES.values():
            for mode in ['manual', 'scheduled']:
                queue_name = queue_template.format(site=site_name, mode=mode)
                consumer_name = f"{consumer_prefix}-{site_name}-{mode}"
                
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
        queue_template: str,
        group: str,
        consumer_prefix: str,
        handler_factory: Callable[[str], Callable[[Dict[str, Any]], None]],
        block_ms: int = 1000,
        read_count: int = 1
    ) -> int:
        """
        注册需要 stream 参数的消费者（使用工厂函数）
        
        Args:
            queue_template: 队列名称模板
            group: 消费者组名
            consumer_prefix: 消费者名称前缀
            handler_factory: 接收 queue_name 返回 handler 的工厂函数
            block_ms: 阻塞时间
            read_count: 每次读取消息数量
            
        Returns:
            注册的消费者数量
        """
        registered_count = 0
        
        for site_name in constants.SUPPORTED_SITES.values():
            for mode in ['manual', 'scheduled']:
                queue_name = queue_template.format(site=site_name, mode=mode)
                consumer_name = f"{consumer_prefix}-{site_name}-{mode}"
                
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

