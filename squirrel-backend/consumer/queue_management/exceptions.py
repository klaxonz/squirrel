"""
队列管理系统异常定义

定义了队列管理系统中使用的所有异常类型，提供清晰的错误分类和处理。
"""

from typing import Optional


class QueueManagementError(Exception):
    """队列管理基础异常类
    
    所有队列管理相关异常的基类，提供统一的异常处理接口。
    """
    
    def __init__(self, message: str, queue_name: Optional[str] = None, details: Optional[dict] = None):
        self.message = message
        self.queue_name = queue_name
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self):
        if self.queue_name:
            return f"{self.message} (queue: {self.queue_name})"
        return self.message
    
    def to_dict(self):
        """转换为字典格式，便于日志记录和调试"""
        return {
            "error_type": self.__class__.__name__,
            "message": self.message,
            "queue_name": self.queue_name,
            "details": self.details
        }


class QueueNotFoundError(QueueManagementError):
    """队列不存在异常
    
    当尝试访问不存在的队列时抛出此异常。
    """
    
    def __init__(self, queue_name: str, available_queues: Optional[list] = None):
        message = f"Queue not found: {queue_name}"
        details = {}
        if available_queues:
            details["available_queues"] = available_queues
            message += f". Available queues: {', '.join(available_queues[:5])}"
            if len(available_queues) > 5:
                message += f" and {len(available_queues) - 5} more"
        
        super().__init__(message, queue_name, details)


class RoutingError(QueueManagementError):
    """路由错误异常
    
    当消息路由失败时抛出此异常。
    """
    
    def __init__(self, message: str, rule_name: Optional[str] = None, 
                 original_message: Optional[dict] = None, cause: Optional[Exception] = None):
        details = {}
        if rule_name:
            details["rule_name"] = rule_name
        if original_message:
            details["original_message"] = original_message
        if cause:
            details["cause"] = str(cause)
            message += f" (caused by: {cause})"
        
        super().__init__(message, details=details)
        self.rule_name = rule_name
        self.original_message = original_message
        self.cause = cause


class PatternMatchError(QueueManagementError):
    """模式匹配错误异常
    
    当队列模式匹配失败时抛出此异常。
    """
    
    def __init__(self, pattern: str, queue_name: Optional[str] = None, cause: Optional[Exception] = None):
        message = f"Pattern match failed: {pattern}"
        if queue_name:
            message += f" for queue: {queue_name}"
        
        details = {"pattern": pattern}
        if cause:
            details["cause"] = str(cause)
            message += f" (caused by: {cause})"
        
        super().__init__(message, queue_name, details)
        self.pattern = pattern
        self.cause = cause


class HandlerRegistrationError(QueueManagementError):
    """处理器注册错误异常
    
    当处理器注册失败时抛出此异常。
    """
    
    def __init__(self, handler_name: str, queue_pattern: str, cause: Optional[Exception] = None):
        message = f"Failed to register handler '{handler_name}' for pattern '{queue_pattern}'"
        
        details = {
            "handler_name": handler_name,
            "queue_pattern": queue_pattern
        }
        
        if cause:
            details["cause"] = str(cause)
            message += f" (caused by: {cause})"
        
        super().__init__(message, details=details)
        self.handler_name = handler_name
        self.queue_pattern = queue_pattern
        self.cause = cause


class MessageSendError(QueueManagementError):
    """消息发送错误异常
    
    当消息发送失败时抛出此异常。
    """
    
    def __init__(self, queue_name: str, message: dict, cause: Optional[Exception] = None):
        error_message = f"Failed to send message to queue: {queue_name}"
        
        details = {
            "message": message,
            "message_type": type(message).__name__
        }
        
        if cause:
            details["cause"] = str(cause)
            error_message += f" (caused by: {cause})"
        
        super().__init__(error_message, queue_name, details)
        self.original_message = message
        self.cause = cause


class ConfigurationError(QueueManagementError):
    """配置错误异常
    
    当队列管理系统配置错误时抛出此异常。
    """
    
    def __init__(self, config_key: str, config_value: Optional[str] = None, 
                 expected_type: Optional[str] = None):
        message = f"Invalid configuration for '{config_key}'"
        
        details = {"config_key": config_key}
        
        if config_value is not None:
            details["config_value"] = config_value
            message += f": {config_value}"
        
        if expected_type:
            details["expected_type"] = expected_type
            message += f" (expected: {expected_type})"
        
        super().__init__(message, details=details)
        self.config_key = config_key
        self.config_value = config_value
        self.expected_type = expected_type


def handle_queue_error(func):
    """队列操作错误处理装饰器
    
    用于统一处理队列操作中的异常，提供标准化的错误处理和日志记录。
    """
    import functools
    import logging
    
    logger = logging.getLogger(__name__)
    
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except QueueManagementError:
            # 队列管理异常直接重新抛出
            raise
        except Exception as e:
            # 其他异常包装为队列管理异常
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            raise QueueManagementError(
                f"Unexpected error in {func.__name__}: {e}",
                details={"function": func.__name__, "args": str(args), "kwargs": str(kwargs)}
            ) from e
    
    return wrapper


def is_retryable_error(error: Exception) -> bool:
    """判断错误是否可重试
    
    Args:
        error: 要判断的异常
        
    Returns:
        bool: 是否可重试
    """
    # 配置错误和模式匹配错误通常不可重试
    if isinstance(error, (ConfigurationError, PatternMatchError, HandlerRegistrationError)):
        return False
    
    # 队列不存在错误可能可重试（如果是动态创建的队列）
    if isinstance(error, QueueNotFoundError):
        return True
    
    # 路由错误和消息发送错误通常可重试
    if isinstance(error, (RoutingError, MessageSendError)):
        return True
    
    # 其他队列管理错误默认可重试
    if isinstance(error, QueueManagementError):
        return True
    
    # 非队列管理异常默认不可重试
    return False


def get_error_context(error: Exception) -> dict:
    """获取错误上下文信息
    
    Args:
        error: 异常对象
        
    Returns:
        dict: 错误上下文信息
    """
    context = {
        "error_type": type(error).__name__,
        "error_message": str(error),
        "retryable": is_retryable_error(error)
    }
    
    if isinstance(error, QueueManagementError):
        context.update(error.to_dict())
    
    return context
