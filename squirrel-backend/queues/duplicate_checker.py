"""
消息队列重复检测工具

直接检查 Redis Stream 队列中是否已存在相同消息，由调用方决定是否使用
"""
import hashlib
import json
import logging
from typing import Callable, Dict, Optional, Any

from core.cache import redis_client

logger = logging.getLogger(__name__)


class MessageDuplicateChecker:
    """消息重复检测工具类
    
    直接检查队列中是否已存在匹配的消息，不需要额外维护标记
    """
    
    def __init__(
        self, 
        queue_name: str,
        match_fn: Callable[[Dict, Dict], bool],
        check_count: Optional[int] = None
    ):
        """
        初始化重复检测器
        
        Args:
            queue_name: 队列名称（Redis Stream key）
            match_fn: 消息匹配函数，接收两个消息字典，返回是否匹配
            check_count: 检查队列中最近的多少条消息，None 表示检查所有消息（默认）
        """
        self.queue_name = queue_name
        self.match_fn = match_fn
        self.check_count = check_count
    
    def is_duplicate(self, message: Dict) -> bool:
        """
        检查消息是否已在队列中
        
        Args:
            message: 要检查的消息内容
            
        Returns:
            True 表示队列中已存在，False 表示不存在
        """
        try:
            # 读取队列中的消息（从新到旧）
            # XREVRANGE key + - [COUNT count]
            if self.check_count is None:
                # 检查所有消息
                messages = redis_client.xrevrange(self.queue_name, '+', '-')
            else:
                # 只检查最近的 N 条消息
                messages = redis_client.xrevrange(
                    self.queue_name, 
                    '+', 
                    '-', 
                    count=self.check_count
                )
            
            if not messages:
                return False
            
            # 检查是否有匹配的消息
            for msg_id, fields in messages:
                try:
                    # 解析消息内容
                    # Redis 返回的 key 可能是 bytes 或 string，需要兼容处理
                    body_str = fields.get(b'body') or fields.get('body')
                    if body_str is None:
                        continue
                    
                    # 转换为字符串
                    if isinstance(body_str, bytes):
                        body_str = body_str.decode('utf-8')
                    
                    existing_message = json.loads(body_str)
                    
                    # 使用自定义匹配函数判断
                    if self.match_fn(message, existing_message):
                        logger.debug(
                            f"Duplicate message found in {self.queue_name}: "
                            f"msg_id={msg_id.decode() if isinstance(msg_id, bytes) else msg_id}"
                        )
                        return True
                        
                except (ValueError, TypeError, KeyError) as e:
                    logger.warning(f"Failed to parse message in queue: {e}")
                    continue
            
            return False
            
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.error(f"Failed to check duplicate in {self.queue_name}: {e}")
            # 检查失败时返回 False，不阻止消息发送
            return False


def create_checker(
    queue_name: str,
    match_fn: Callable[[Dict, Dict], bool],
    check_count: Optional[int] = None
) -> MessageDuplicateChecker:
    """
    创建重复检测器的工厂函数
    
    Args:
        queue_name: 队列名称
        match_fn: 消息匹配函数
        check_count: 检查最近多少条消息，None 表示检查所有消息（默认）
        
    Returns:
        MessageDuplicateChecker 实例
    """
    return MessageDuplicateChecker(queue_name, match_fn, check_count)


def create_simple_checker(
    queue_name: str,
    key_fn: Callable[[Dict], Any],
    check_count: Optional[int] = None
) -> MessageDuplicateChecker:
    """
    创建简单的重复检测器（基于 key 相等）
    
    这是一个便捷函数，用于常见场景：基于某个字段或字段组合判断重复
    
    Args:
        queue_name: 队列名称
        key_fn: 从消息中提取唯一标识的函数
        check_count: 检查最近多少条消息，None 表示检查所有消息（默认）
        
    Returns:
        MessageDuplicateChecker 实例
        
    Example:
        # 基于 subscription_id 判断重复（检查所有消息）
        checker = create_simple_checker(
            'subscription_update',
            key_fn=lambda msg: msg['body']['subscription_id']
        )
        
        # 只检查最近100条消息（适用于高频队列）
        checker = create_simple_checker(
            'subscription_update',
            key_fn=lambda msg: msg['body']['subscription_id'],
            check_count=100
        )
    """
    def match_fn(msg1: Dict, msg2: Dict) -> bool:
        try:
            return key_fn(msg1) == key_fn(msg2)
        except (ValueError, TypeError, KeyError):
            return False
    
    return MessageDuplicateChecker(queue_name, match_fn, check_count)

