import logging
from typing import Callable, Union, List
from .exceptions import HandlerRegistrationError, RoutingError
from .manager import QueueManager
from .router import MessageRouter

logger = logging.getLogger(__name__)


def queue_handler(queues: Union[str, List[str]], **actor_kwargs) -> Callable:
    """队列处理器装饰器
    
    用于注册队列处理函数，支持单个队列、多个队列和模式匹配。
    
    Args:
        queues: 队列名称或队列名称列表，支持通配符 *
        **actor_kwargs: dramatiq actor 参数
        
    Returns:
        Callable: 装饰后的函数
        
    Examples:
        # 单个队列
        @queue_handler("video_download")
        def handle_download(message):
            pass
        
        # 多个队列
        @queue_handler(["queue1", "queue2"])
        def handle_multiple(message):
            pass
        
        # 模式匹配
        @queue_handler("video_extract_*")
        def handle_video_pattern(message, queue_name):
            pass
        
        # 带参数
        @queue_handler("high_priority", max_retries=5, time_limit=300)
        def handle_priority(message):
            pass
    """
    def decorator(func: Callable) -> Callable:
        queue_list = None
        try:
            queue_list = queues if isinstance(queues, list) else [queues]

            for queue_pattern in queue_list:
                QueueManager.register_handler(queue_pattern, func, **actor_kwargs)

            setattr(func, "_queue_handler_info", {
                "queues": queue_list,
                "actor_kwargs": actor_kwargs,
                "registered": True
            })

            logger.debug(f"Registered queue handler {func.__name__} for queues: {queue_list}")

        except Exception as e:
            logger.error(f"Failed to register queue handler {func.__name__}: {e}")
            safe_queues = queue_list if queue_list is not None else (queues if isinstance(queues, list) else [queues])
            setattr(func, "_queue_handler_info", {
                "queues": safe_queues,
                "actor_kwargs": actor_kwargs,
                "registered": False,
                "error": str(e)
            })
            raise HandlerRegistrationError(
                handler_name=func.__name__,
                queue_pattern=str(queues),
                cause=e
            )
        
        return func
    
    return decorator


def routing_rule(rule_name: str) -> Callable:
    """路由规则装饰器
    
    用于注册消息路由规则。
    
    Args:
        rule_name: 路由规则名称
        
    Returns:
        Callable: 装饰后的函数
        
    Examples:
        @routing_rule("video_processing")
        def route_video(message):
            url = message.get('url', '')
            if 'bilibili.com' in url:
                return 'video_extract_bilibili'
            return 'video_extract_default'
    """
    def decorator(func: Callable) -> Callable:
        try:
            MessageRouter.register_rule(rule_name, func)
            
            setattr(func, "_routing_rule_info", {
                "rule_name": rule_name,
                "registered": True
            })
            
            logger.debug(f"Registered routing rule {rule_name} with function {func.__name__}")
            
        except Exception as e:
            logger.error(f"Failed to register routing rule {rule_name}: {e}")
            setattr(func, "_routing_rule_info", {
                "rule_name": rule_name,
                "registered": False,
                "error": str(e)
            })
            raise RoutingError(
                f"Failed to register routing rule: {rule_name}",
                rule_name=rule_name,
                cause=e
            )
        
        return func
    
    return decorator

