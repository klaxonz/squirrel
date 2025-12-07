"""
提取链路统一异常体系
"""
from typing import Optional, Dict, Any
from datetime import datetime


class ExtractionError(Exception):
    """
    提取错误基类
    
    提供：
    - 错误分类（可重试/不可重试）
    - 上下文信息
    - 时间戳
    """
    
    def __init__(
        self,
        message: str,
        retryable: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.context = context or {}
        self.timestamp = datetime.now()
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.message}"
    
    def __repr__(self):
        return (
            f"{self.__class__.__name__}("
            f"message='{self.message}', "
            f"retryable={self.retryable}, "
            f"context={self.context})"
        )


# ========== 数据转换相关异常 ==========

class DataTransformError(ExtractionError):
    """
    数据转换错误
    
    场景：
    - 插件Video对象转换为VideoDTO失败
    - 数据格式不符合预期
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


class ValidationError(ExtractionError):
    """
    数据验证错误
    
    场景：
    - URL格式错误
    - 必填字段缺失
    - 数据类型不匹配
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


# ========== 网络相关异常（可重试） ==========

class NetworkError(ExtractionError):
    """
    网络错误
    
    场景：
    - 连接超时
    - DNS解析失败
    - 服务器无响应
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


class RateLimitError(ExtractionError):
    """
    限流错误
    
    场景：
    - 请求过于频繁
    - 触发站点限流
    """
    
    def __init__(self, message: str, retry_after: int = 60, **kwargs):
        super().__init__(message, retryable=True, **kwargs)
        self.retry_after = retry_after


# ========== 业务逻辑异常（不可重试） ==========

class ResourceNotFoundError(ExtractionError):
    """
    资源不存在
    
    场景：
    - 视频已删除
    - 频道不存在
    - 页面404
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


class PermissionError(ExtractionError):
    """
    权限错误
    
    场景：
    - 需要登录
    - 会员专享内容
    - 地区限制
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


# ========== 系统错误（可重试） ==========

class DatabaseError(ExtractionError):
    """
    数据库错误
    
    场景：
    - 连接失败
    - 查询超时
    - 事务失败
    """
    
    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


class CircuitBreakerOpenError(ExtractionError):
    """
    熔断器打开错误
    
    场景：
    - 服务不可用
    - 失败率过高
    """
    
    def __init__(self, service_name: str, **kwargs):
        message = f"Circuit breaker is open for {service_name}"
        super().__init__(message, retryable=False, **kwargs)
        self.service_name = service_name


# ========== Pipeline相关异常 ==========

class PipelineError(ExtractionError):
    """
    Pipeline执行错误
    
    场景：
    - Stage执行失败
    - 上下文数据缺失
    - 流程中断
    """
    
    def __init__(self, message: str, stage_name: Optional[str] = None, **kwargs):
        super().__init__(message, retryable=False, **kwargs)
        self.stage_name = stage_name


class StageExecutionError(PipelineError):
    """
    Stage执行错误
    
    更具体的Pipeline Stage错误
    """
    pass
