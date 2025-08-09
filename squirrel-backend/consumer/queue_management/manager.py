"""
队列管理器

提供统一的队列管理接口，负责队列注册、消息发送和状态监控。
"""

import logging
from typing import Callable, Dict, Any, Optional, List
from .registry import QueueRegistry
from .exceptions import (
    QueueNotFoundError, 
    MessageSendError, 
    HandlerRegistrationError,
    handle_queue_error
)

logger = logging.getLogger(__name__)


class QueueManager:
    """通用队列管理器
    
    提供统一的队列管理接口，包括：
    - 队列处理器注册
    - 消息发送
    - 队列状态监控
    - 动态队列创建
    """
    
    # 统计信息
    _stats = {
        "messages_sent": 0,
        "queues_created": 0,
        "handlers_registered": 0,
        "send_errors": 0
    }
    
    @staticmethod
    @handle_queue_error
    def register_handler(queue_pattern: str, handler: Callable, **actor_kwargs) -> None:
        """注册队列处理器
        
        支持精确队列名称和模式匹配。
        
        Args:
            queue_pattern: 队列名称或模式，支持通配符 *
            handler: 处理函数
            **actor_kwargs: dramatiq actor 的额外参数
            
        Raises:
            HandlerRegistrationError: 注册失败时抛出
            
        Examples:
            # 精确队列名称
            QueueManager.register_handler("video_download", handle_download)
            
            # 模式匹配
            QueueManager.register_handler("video_extract_*", handle_extract)
            
            # 带参数
            QueueManager.register_handler(
                "high_priority_*", 
                handle_priority,
                max_retries=5,
                time_limit=600
            )
        """
        try:
            # 验证参数
            QueueManager._validate_handler_registration(queue_pattern, handler)
            
            if '*' in queue_pattern or '?' in queue_pattern:
                # 模式匹配队列
                QueueRegistry.register_pattern(queue_pattern, handler, **actor_kwargs)
                logger.info(f"Registered pattern handler: {queue_pattern}")
            else:
                # 精确队列名称 - 使用唯一actor名称避免冲突
                import dramatiq
                actor_name = f"{handler.__name__}__{queue_pattern}"
                actor = dramatiq.actor(queue_name=queue_pattern, actor_name=actor_name, **actor_kwargs)(handler)
                QueueRegistry.register_queue(queue_pattern, actor, handler)
                logger.info(f"Registered exact handler: {queue_pattern} with actor name: {actor_name}")
            
            QueueManager._stats["handlers_registered"] += 1
            
        except Exception as e:
            logger.error(f"Failed to register handler for {queue_pattern}: {e}")
            raise HandlerRegistrationError(
                handler_name=getattr(handler, '__name__', str(handler)),
                queue_pattern=queue_pattern,
                cause=e
            )
    
    @staticmethod
    def _validate_handler_registration(queue_pattern: str, handler: Callable) -> None:
        """验证处理器注册参数
        
        Args:
            queue_pattern: 队列模式
            handler: 处理函数
            
        Raises:
            ValueError: 参数无效时抛出
        """
        if not queue_pattern or not isinstance(queue_pattern, str):
            raise ValueError("queue_pattern must be a non-empty string")
        
        if not callable(handler):
            raise ValueError("handler must be callable")
        
        # 验证队列名称格式（对于精确匹配）
        if '*' not in queue_pattern and '?' not in queue_pattern:
            if not QueueRegistry.validate_queue_name(queue_pattern):
                raise ValueError(f"Invalid queue name format: {queue_pattern}")
    
    @staticmethod
    @handle_queue_error
    def create_queue(queue_name: str, handler: Callable, **actor_kwargs) -> Any:
        """动态创建队列
        
        Args:
            queue_name: 队列名称
            handler: 处理函数
            **actor_kwargs: dramatiq actor 的额外参数
            
        Returns:
            Any: 创建的actor对象
            
        Raises:
            HandlerRegistrationError: 创建失败时抛出
        """
        try:
            # 验证参数
            if not QueueRegistry.validate_queue_name(queue_name):
                raise ValueError(f"Invalid queue name: {queue_name}")
            
            if not callable(handler):
                raise ValueError("handler must be callable")
            
            # 检查队列是否已存在
            if QueueRegistry.has_queue(queue_name):
                logger.debug(f"Queue {queue_name} already exists, returning existing actor")
                return QueueRegistry.get_actor(queue_name)
            
            # 创建新队列 - 使用唯一actor名称避免冲突
            import dramatiq
            actor_name = f"{handler.__name__}__{queue_name}"
            actor = dramatiq.actor(queue_name=queue_name, actor_name=actor_name, **actor_kwargs)(handler)
            QueueRegistry.register_queue(queue_name, actor, handler)

            QueueManager._stats["queues_created"] += 1
            logger.info(f"Created dynamic queue: {queue_name}, actor: {actor_name}")

            return actor
            
        except Exception as e:
            logger.error(f"Failed to create queue {queue_name}: {e}")
            raise HandlerRegistrationError(
                handler_name=getattr(handler, '__name__', str(handler)),
                queue_pattern=queue_name,
                cause=e
            )
    
    @staticmethod
    @handle_queue_error
    def send_message(queue_name: str, message: Any) -> None:
        """发送消息到指定队列
        
        Args:
            queue_name: 目标队列名称
            message: 要发送的消息
            
        Raises:
            QueueNotFoundError: 队列不存在时抛出
            MessageSendError: 消息发送失败时抛出
            
        Examples:
            QueueManager.send_message("video_download", {
                "video_id": 123,
                "url": "https://example.com/video.mp4"
            })
        """
        try:
            # 验证队列名称
            if not queue_name or not isinstance(queue_name, str):
                raise ValueError("queue_name must be a non-empty string")
            
            # 获取actor
            actor = QueueRegistry.get_actor(queue_name)
            if not actor:
                available_queues = QueueManager._get_available_queue_names()
                raise QueueNotFoundError(queue_name, available_queues)
            
            # 发送消息
            actor.send(message)
            QueueManager._stats["messages_sent"] += 1
            
            logger.debug(f"Message sent to queue {queue_name}: {type(message).__name__}")
            
        except QueueNotFoundError:
            QueueManager._stats["send_errors"] += 1
            raise
        except Exception as e:
            QueueManager._stats["send_errors"] += 1
            logger.error(f"Failed to send message to {queue_name}: {e}")
            raise MessageSendError(queue_name, message, cause=e)
    
    @staticmethod
    def _get_available_queue_names() -> List[str]:
        """获取可用的队列名称列表
        
        Returns:
            List[str]: 可用队列名称列表
        """
        info = QueueRegistry.get_all_info()
        available = []
        available.extend(info.get("exact_queues", []))
        available.extend(info.get("dynamic_queues", []))
        
        # 添加模式队列的示例
        for pattern in info.get("pattern_queues", []):
            example = pattern.replace("*", "example")
            available.append(f"{example} (pattern: {pattern})")
        
        return available
    
    @staticmethod
    def send_message_safe(queue_name: str, message: Any, 
                         fallback_queue: Optional[str] = None) -> bool:
        """安全发送消息，失败时不抛出异常
        
        Args:
            queue_name: 目标队列名称
            message: 要发送的消息
            fallback_queue: 备用队列名称
            
        Returns:
            bool: 是否发送成功
        """
        try:
            QueueManager.send_message(queue_name, message)
            return True
        except QueueNotFoundError:
            if fallback_queue:
                try:
                    QueueManager.send_message(fallback_queue, message)
                    logger.warning(f"Message sent to fallback queue {fallback_queue} "
                                 f"(original queue {queue_name} not found)")
                    return True
                except Exception as e:
                    logger.error(f"Failed to send to fallback queue {fallback_queue}: {e}")
            else:
                logger.error(f"Queue {queue_name} not found and no fallback provided")
            return False
        except Exception as e:
            logger.error(f"Failed to send message to {queue_name}: {e}")
            return False
    
    @staticmethod
    def batch_send_messages(queue_name: str, messages: List[Any]) -> Dict[str, Any]:
        """批量发送消息
        
        Args:
            queue_name: 目标队列名称
            messages: 消息列表
            
        Returns:
            Dict[str, Any]: 发送结果统计
        """
        results = {
            "total": len(messages),
            "success": 0,
            "failed": 0,
            "errors": []
        }
        
        for i, message in enumerate(messages):
            try:
                QueueManager.send_message(queue_name, message)
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append({
                    "index": i,
                    "message": message,
                    "error": str(e)
                })
                logger.error(f"Failed to send message {i} to {queue_name}: {e}")
        
        logger.info(f"Batch send to {queue_name}: {results['success']}/{results['total']} successful")
        return results
    
    @staticmethod
    def get_queue_info() -> Dict[str, Any]:
        """获取所有队列的统计信息
        
        Returns:
            Dict[str, Any]: 队列统计信息
        """
        registry_info = QueueRegistry.get_all_info()
        
        return {
            **registry_info,
            "stats": QueueManager._stats.copy(),
            "total_registered": (
                registry_info.get("total_exact", 0) + 
                registry_info.get("total_patterns", 0)
            )
        }
    
    @staticmethod
    def get_queue_health(queue_name: str) -> Dict[str, Any]:
        """检查队列健康状态
        
        Args:
            queue_name: 队列名称
            
        Returns:
            Dict[str, Any]: 队列健康状态信息
        """
        health = {
            "queue_name": queue_name,
            "exists": False,
            "has_actor": False,
            "has_handler": False,
            "matching_patterns": [],
            "is_dynamic": False
        }
        
        try:
            # 检查队列是否存在
            health["exists"] = QueueRegistry.has_queue(queue_name)
            
            if health["exists"]:
                # 检查actor
                actor = QueueRegistry.get_actor(queue_name)
                health["has_actor"] = actor is not None
                
                # 检查处理器
                handler = QueueRegistry.get_handler(queue_name)
                health["has_handler"] = handler is not None
                
                # 检查是否是动态队列
                registry_info = QueueRegistry.get_all_info()
                health["is_dynamic"] = queue_name in registry_info.get("dynamic_queues", [])
            
            # 获取匹配的模式
            health["matching_patterns"] = QueueRegistry.get_matching_patterns(queue_name)
            
        except Exception as e:
            health["error"] = str(e)
            logger.error(f"Error checking health for queue {queue_name}: {e}")
        
        return health
    
    @staticmethod
    def reset_stats() -> None:
        """重置统计信息"""
        QueueManager._stats = {
            "messages_sent": 0,
            "queues_created": 0,
            "handlers_registered": 0,
            "send_errors": 0
        }
        logger.info("Queue manager stats reset")
    
    @staticmethod
    def cleanup() -> None:
        """清理资源
        
        清空动态队列缓存，重置统计信息。
        """
        QueueRegistry.clear_cache()
        QueueManager.reset_stats()
        logger.info("Queue manager cleanup completed")
