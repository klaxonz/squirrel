"""
队列管理装饰器

提供简洁的队列处理器和路由规则注册方式。
"""

import logging
from typing import Callable, Union, List, Optional, Any
from functools import wraps
from .manager import QueueManager
from .router import MessageRouter
from .exceptions import HandlerRegistrationError, RoutingError

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
        try:
            # 确保queues是列表
            queue_list = queues if isinstance(queues, list) else [queues]
            
            # 为每个队列注册处理器
            for queue_pattern in queue_list:
                QueueManager.register_handler(queue_pattern, func, **actor_kwargs)
            
            # 添加元数据到函数
            func._queue_handler_info = {
                "queues": queue_list,
                "actor_kwargs": actor_kwargs,
                "registered": True
            }
            
            logger.debug(f"Registered queue handler {func.__name__} for queues: {queue_list}")
            
        except Exception as e:
            logger.error(f"Failed to register queue handler {func.__name__}: {e}")
            # 添加错误信息到函数
            func._queue_handler_info = {
                "queues": queue_list if 'queue_list' in locals() else queues,
                "actor_kwargs": actor_kwargs,
                "registered": False,
                "error": str(e)
            }
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
            # 注册路由规则
            MessageRouter.register_rule(rule_name, func)
            
            # 添加元数据到函数
            func._routing_rule_info = {
                "rule_name": rule_name,
                "registered": True
            }
            
            logger.debug(f"Registered routing rule {rule_name} with function {func.__name__}")
            
        except Exception as e:
            logger.error(f"Failed to register routing rule {rule_name}: {e}")
            # 添加错误信息到函数
            func._routing_rule_info = {
                "rule_name": rule_name,
                "registered": False,
                "error": str(e)
            }
            raise RoutingError(
                f"Failed to register routing rule: {rule_name}",
                rule_name=rule_name,
                cause=e
            )
        
        return func
    
    return decorator


def conditional_queue_handler(condition_func: Callable[[Any], bool], 
                            true_queues: Union[str, List[str]], 
                            false_queues: Union[str, List[str]], 
                            **actor_kwargs) -> Callable:
    """条件队列处理器装饰器
    
    根据条件函数的结果决定注册到哪些队列。
    
    Args:
        condition_func: 条件判断函数
        true_queues: 条件为真时的队列
        false_queues: 条件为假时的队列
        **actor_kwargs: dramatiq actor 参数
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        try:
            # 根据条件决定注册哪些队列
            if condition_func():
                selected_queues = true_queues
            else:
                selected_queues = false_queues
            
            # 使用标准的queue_handler装饰器
            return queue_handler(selected_queues, **actor_kwargs)(func)
            
        except Exception as e:
            logger.error(f"Failed to register conditional queue handler {func.__name__}: {e}")
            raise HandlerRegistrationError(
                handler_name=func.__name__,
                queue_pattern=f"conditional({true_queues}, {false_queues})",
                cause=e
            )
    
    return decorator


def retry_on_failure(max_retries: int = 3, 
                    retry_delay: float = 1.0, 
                    exponential_backoff: bool = True) -> Callable:
    """重试装饰器
    
    为队列处理器添加重试机制。
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 重试延迟（秒）
        exponential_backoff: 是否使用指数退避
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # 计算延迟时间
                        if exponential_backoff:
                            delay = retry_delay * (2 ** attempt)
                        else:
                            delay = retry_delay
                        
                        logger.warning(
                            f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay} seconds..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            # 重新抛出最后一个异常
            raise last_exception
        
        # 添加重试信息到函数
        wrapper._retry_info = {
            "max_retries": max_retries,
            "retry_delay": retry_delay,
            "exponential_backoff": exponential_backoff
        }
        
        return wrapper
    
    return decorator


def log_execution(log_level: str = "INFO", 
                 include_args: bool = False, 
                 include_result: bool = False) -> Callable:
    """执行日志装饰器
    
    为队列处理器添加执行日志。
    
    Args:
        log_level: 日志级别
        include_args: 是否包含参数信息
        include_result: 是否包含返回结果
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            start_time = time.time()
            
            # 构建日志消息
            log_msg = f"Executing {func.__name__}"
            if include_args and args:
                log_msg += f" with args: {args[:2]}..."  # 只显示前两个参数
            
            # 记录开始日志
            getattr(logger, log_level.lower())(log_msg)
            
            try:
                result = func(*args, **kwargs)
                
                # 记录成功日志
                duration = time.time() - start_time
                success_msg = f"Completed {func.__name__} in {duration:.3f}s"
                if include_result and result is not None:
                    success_msg += f" with result: {str(result)[:100]}..."
                
                getattr(logger, log_level.lower())(success_msg)
                
                return result
                
            except Exception as e:
                # 记录错误日志
                duration = time.time() - start_time
                error_msg = f"Failed {func.__name__} after {duration:.3f}s: {e}"
                logger.error(error_msg)
                raise
        
        # 添加日志信息到函数
        wrapper._log_info = {
            "log_level": log_level,
            "include_args": include_args,
            "include_result": include_result
        }
        
        return wrapper
    
    return decorator


def validate_message(schema: Optional[Any] = None, 
                    required_fields: Optional[List[str]] = None) -> Callable:
    """消息验证装饰器
    
    验证队列消息的格式和内容。
    
    Args:
        schema: Pydantic模型或其他验证schema
        required_fields: 必需字段列表
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(message, *args, **kwargs):
            try:
                # 基本类型检查
                if not isinstance(message, dict):
                    raise ValueError(f"Message must be a dict, got {type(message)}")
                
                # 检查必需字段
                if required_fields:
                    missing_fields = [field for field in required_fields if field not in message]
                    if missing_fields:
                        raise ValueError(f"Missing required fields: {missing_fields}")
                
                # Schema验证
                if schema:
                    try:
                        # 尝试Pydantic验证
                        if hasattr(schema, 'model_validate'):
                            validated_message = schema.model_validate(message)
                            message = validated_message.model_dump()
                        elif hasattr(schema, 'parse_obj'):
                            validated_message = schema.parse_obj(message)
                            message = validated_message.dict()
                        else:
                            # 其他验证方式
                            validated_message = schema(message)
                            if hasattr(validated_message, 'dict'):
                                message = validated_message.dict()
                    except Exception as e:
                        raise ValueError(f"Message validation failed: {e}")
                
                return func(message, *args, **kwargs)
                
            except Exception as e:
                logger.error(f"Message validation failed for {func.__name__}: {e}")
                raise
        
        # 添加验证信息到函数
        wrapper._validation_info = {
            "schema": schema,
            "required_fields": required_fields
        }
        
        return wrapper
    
    return decorator


def performance_monitor(threshold_seconds: float = 5.0) -> Callable:
    """性能监控装饰器
    
    监控队列处理器的执行时间，超过阈值时发出警告。
    
    Args:
        threshold_seconds: 性能阈值（秒）
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                
                if duration > threshold_seconds:
                    logger.warning(
                        f"Performance warning: {func.__name__} took {duration:.3f}s "
                        f"(threshold: {threshold_seconds}s)"
                    )
                else:
                    logger.debug(f"{func.__name__} completed in {duration:.3f}s")
        
        # 添加性能监控信息到函数
        wrapper._performance_info = {
            "threshold_seconds": threshold_seconds
        }
        
        return wrapper
    
    return decorator


# 组合装饰器
def robust_queue_handler(queues: Union[str, List[str]], 
                        max_retries: int = 3,
                        required_fields: Optional[List[str]] = None,
                        performance_threshold: float = 5.0,
                        **actor_kwargs) -> Callable:
    """健壮的队列处理器装饰器
    
    组合多个装饰器，提供完整的队列处理功能。
    
    Args:
        queues: 队列名称或列表
        max_retries: 最大重试次数
        required_fields: 必需字段列表
        performance_threshold: 性能阈值
        **actor_kwargs: dramatiq actor 参数
        
    Returns:
        Callable: 装饰后的函数
    """
    def decorator(func: Callable) -> Callable:
        # 应用多个装饰器
        decorated_func = func
        
        # 性能监控
        decorated_func = performance_monitor(performance_threshold)(decorated_func)
        
        # 消息验证
        if required_fields:
            decorated_func = validate_message(required_fields=required_fields)(decorated_func)
        
        # 重试机制
        decorated_func = retry_on_failure(max_retries=max_retries)(decorated_func)
        
        # 执行日志
        decorated_func = log_execution()(decorated_func)
        
        # 队列处理器注册
        decorated_func = queue_handler(queues, **actor_kwargs)(decorated_func)
        
        return decorated_func
    
    return decorator
