"""
消息队列路由器

基于插件注册表动态路由，消除硬编码
"""
import logging
from typing import Dict, Any
from pydantic import BaseModel
from utils import url_helper
from mq.producer import RedisStreamProducer
from mq.queue_config import get_queue_config, QueueType, QueueMode

logger = logging.getLogger()


class MessageRouter:
    """消息路由器 - 基于插件注册表动态路由"""
    
    def __init__(self, queue_type: QueueType):
        """
        Args:
            queue_type: 队列类型枚举
        """
        self.queue_type = queue_type
        self.producer = RedisStreamProducer()
        self.config = get_queue_config()
    
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
        site = self.config.get_site_by_domain(domain)
        if not site:
            raise ValueError(f"Unsupported domain: {domain}")
        
        mode = QueueMode.MANUAL if is_manual else QueueMode.SCHEDULED
        return self.config.build_queue_name(self.queue_type, site, mode)


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


# 预定义路由器（延迟初始化，在插件加载后调用 ensure_queue_config_initialized）
video_extract_router = MessageRouter(QueueType.VIDEO_EXTRACT)
subscription_update_router = MessageRouter(QueueType.SUBSCRIPTION_UPDATE)

