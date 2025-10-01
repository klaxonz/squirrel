"""
消息队列路由器

提供统一的消息路由功能，支持：
- 基于域名的路由
- 手动/定时模式区分
- 统一的消息格式处理
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel
from common import constants
from utils import url_helper
from mq.producer import RedisStreamProducer

logger = logging.getLogger()


class MessageRouter:
    """消息路由器基类"""
    
    def __init__(self, queue_prefix: str, queue_mapping: Dict[str, Dict[str, str]]):
        """
        Args:
            queue_prefix: 队列前缀，如 'video::extract' 或 'subscription::update'
            queue_mapping: 域名到队列的映射
        """
        self.queue_prefix = queue_prefix
        self.queue_mapping = queue_mapping
        self.producer = RedisStreamProducer()
    
    def route(self, message: Dict[str, Any], url: str, is_manual: bool) -> None:
        """
        路由消息到对应的域队列
        
        Args:
            message: 原始消息
            url: 用于解析域名的 URL
            is_manual: 是否为手动触发
        """
        queue_name = self._resolve_queue(url, is_manual)
        self.producer.send(queue_name, message)
        logger.debug(f"Routed message to {queue_name}")
    
    def _resolve_queue(self, url: str, is_manual: bool) -> str:
        """解析队列名称"""
        domain = url_helper.extract_top_level_domain(url)
        mapping = self.queue_mapping.get(domain)
        if not mapping:
            raise ValueError(f"Unsupported domain: {domain}")
        
        mode = 'manual' if is_manual else 'scheduled'
        queue_name = mapping.get(mode)
        if not queue_name:
            raise ValueError(f"No queue mapping for domain {domain}, mode {mode}")
        
        return queue_name


class DirectMessageSender:
    """直接消息发送器（不经过 Message 表）"""
    
    def __init__(self):
        self.producer = RedisStreamProducer()
    
    def send(self, queue: str, dto: BaseModel) -> None:
        """
        发送 Pydantic DTO 到队列
        
        Args:
            queue: 队列名称
            dto: Pydantic 模型实例
        """
        message = dto.model_dump_json()
        self.producer.send(queue, {"body": message})
        logger.debug(f"Sent message to {queue}")


# 预定义路由器
video_extract_router = MessageRouter(
    queue_prefix='video::extract',
    queue_mapping=constants.DOMAIN_QUEUE_MAPPING
)

subscription_update_router = MessageRouter(
    queue_prefix='subscription::update',
    queue_mapping=constants.SUBSCRIPTION_UPDATE_DOMAIN_QUEUE_MAPPING
)

