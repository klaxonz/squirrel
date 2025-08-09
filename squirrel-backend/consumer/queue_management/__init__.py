"""
通用队列管理系统

这个模块提供了一个通用的队列管理系统，用于替代原有的动态队列创建方式。
主要特性：
- 统一的队列注册和管理
- 模式匹配支持
- 智能消息路由
- 内存优化
- 向后兼容

使用示例:
    from consumer.queue_management.decorators import queue_handler
    from consumer.queue_management.manager import QueueManager
    
    @queue_handler("video_download")
    def handle_download(message):
        print(f"Processing download: {message}")
    
    QueueManager.send_message("video_download", {"video_id": 123})
"""

from .manager import QueueManager
from .registry import QueueRegistry
from .router import MessageRouter
from .decorators import queue_handler, routing_rule
from .exceptions import (
    QueueManagementError,
    QueueNotFoundError,
    RoutingError,
    PatternMatchError
)

__version__ = "1.0.0"
__author__ = "Augment Agent"

__all__ = [
    # Core components
    "QueueManager",
    "QueueRegistry", 
    "MessageRouter",
    
    # Decorators
    "queue_handler",
    "routing_rule",
    
    # Exceptions
    "QueueManagementError",
    "QueueNotFoundError",
    "RoutingError",
    "PatternMatchError",
]
