"""
直接域队列生产者

职责：根据URL域名直接发送消息到对应的域队列，消除入口队列的中间层
支持视频提取和订阅更新两种队列类型
"""
import logging
from typing import Dict, Any

from mq.producer import RedisStreamProducer
from mq.queue_config import get_queue_config, QueueType, QueueMode
from utils import url_helper
from utils.site_catalog import SiteCatalog

logger = logging.getLogger()


class DirectDomainProducer:
    """直接发送到域队列的生产者"""
    
    def __init__(self):
        self.producer = RedisStreamProducer()
        self.config = get_queue_config()
    
    def send_video_extract(
        self,
        message: Dict[str, Any],
        url: str,
        priority: str  # "manual" | "incr" | "full"
    ) -> str:
        """
        发送视频提取消息到域队列
        
        Args:
            message: 消息内容（已包含trace_id等）
            url: 视频URL，用于解析域名
            priority: 优先级 ("manual" | "incr" | "full")
            
        Returns:
            消息ID
            
        Raises:
            ValueError: 不支持的域名或站点被禁用
        """
        domain = url_helper.extract_top_level_domain(url)
        
        # 检查站点是否启用
        if not SiteCatalog.is_site_enabled(domain=domain):
            raise ValueError(f"Site disabled: {domain}")
        
        site = self.config.get_site_by_domain(domain)
        if not site:
            raise ValueError(f"Unsupported domain: {domain}")
        
        # 映射优先级到队列模式
        mode_mapping = {
            "manual": QueueMode.MANUAL,
            "incr": QueueMode.INCREMENTAL,
            "full": QueueMode.FULL
        }
        
        if priority not in mode_mapping:
            raise ValueError(f"Invalid priority: {priority}, must be one of {list(mode_mapping.keys())}")
        
        mode = mode_mapping[priority]
        
        # 构建域队列名称
        queue_name = self.config.build_queue_name(QueueType.VIDEO_EXTRACT, site, mode)
        
        # 发送消息
        msg_id = self.producer.send(queue_name, message)
        logger.debug(f"Sent video extract message to {queue_name}, msg_id={msg_id}")
        
        return msg_id
    
    def send_subscription_update(
        self,
        message: Dict[str, Any],
        url: str,
        priority: str  # "manual" | "incr" | "full"
    ) -> str:
        """
        发送订阅更新消息到域队列
        
        Args:
            message: 消息内容（已包含trace_id等）
            url: 订阅URL，用于解析域名
            priority: 优先级 ("manual" | "incr" | "full")
            
        Returns:
            消息ID
            
        Raises:
            ValueError: 不支持的域名或站点被禁用
        """
        domain = url_helper.extract_top_level_domain(url)
        
        # 检查站点是否启用
        if not SiteCatalog.is_site_enabled(domain=domain):
            raise ValueError(f"Site disabled: {domain}")
        
        site = self.config.get_site_by_domain(domain)
        if not site:
            raise ValueError(f"Unsupported domain: {domain}")
        
        # 映射优先级到队列模式
        mode_mapping = {
            "manual": QueueMode.MANUAL,
            "incr": QueueMode.INCREMENTAL,
            "full": QueueMode.FULL
        }
        
        if priority not in mode_mapping:
            raise ValueError(f"Invalid priority: {priority}, must be one of {list(mode_mapping.keys())}")
        
        mode = mode_mapping[priority]
        
        # 构建域队列名称
        queue_name = self.config.build_queue_name(QueueType.SUBSCRIPTION_UPDATE, site, mode)
        
        # 发送消息
        msg_id = self.producer.send(queue_name, message)
        logger.debug(f"Sent subscription update message to {queue_name}, msg_id={msg_id}")
        
        return msg_id


# 全局单例
direct_domain_producer = DirectDomainProducer()
