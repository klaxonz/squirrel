"""SDK 统一异常体系

提供插件层统一的异常类，支持错误分类、重试判断和上下文传递。
"""
from enum import Enum
from typing import Optional, Dict, Any


class ErrorCategory(str, Enum):
    """错误分类，用于决定是否重试和错误展示"""
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    VIP = "vip"
    NOT_FOUND = "not_found"
    PARSE = "parse"
    UNKNOWN = "unknown"


class PluginError(Exception):
    """插件错误基类"""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        retryable: bool = False,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.retryable = retryable
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "context": self.context
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, category={self.category.value})"


class NetworkError(PluginError):
    """网络错误（连接超时、DNS失败等），可重试"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.NETWORK, retryable=True, context=context)


class RateLimitError(PluginError):
    """限流错误，可重试（延迟后）"""

    def __init__(
        self,
        message: str,
        retry_after: int = 60,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message, ErrorCategory.RATE_LIMIT, retryable=True, context=context)
        self.retry_after = retry_after


class AuthError(PluginError):
    """认证错误（需要登录），不可重试"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.AUTH, retryable=False, context=context)


class VipError(PluginError):
    """VIP权限错误（需要VIP），不可重试"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.VIP, retryable=False, context=context)


class NotFoundError(PluginError):
    """资源不存在（视频已删除、404等），不可重试"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.NOT_FOUND, retryable=False, context=context)


class ParseError(PluginError):
    """解析错误（页面结构变化、数据格式错误等），不可重试"""

    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.PARSE, retryable=False, context=context)


class NoSubtitlesError(PluginError):
    def __init__(self, message: str = 'No subtitles available', context: Optional[Dict[str, Any]] = None):
        super().__init__(message, ErrorCategory.NOT_FOUND, retryable=False, context=context)
