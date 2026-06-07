"""链路追踪工具模块

提供统一的 trace_id 管理，支持跨线程、协程和消息队列的链路追踪。

核心功能：
- 生成唯一的 trace_id
- 在 context 中存储和获取 trace_id
- 提供装饰器和 context manager 来设置 trace_id
"""

import uuid
from collections.abc import Callable
from contextvars import ContextVar, Token
from functools import wraps
from typing import Any

# 使用 ContextVar 存储 trace_id，支持异步和线程隔离
_trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


def generate_trace_id() -> str:
    """生成唯一的 trace_id

    Returns:
        32 字符的十六进制字符串（UUID 的十六进制表示）

    """
    return uuid.uuid4().hex


def get_trace_id() -> str | None:
    """获取当前上下文的 trace_id

    Returns:
        当前的 trace_id，如果未设置则返回 None

    """
    return _trace_id_var.get()


def set_trace_id(trace_id: str | None) -> None:
    """设置当前上下文的 trace_id

    Args:
        trace_id: 要设置的 trace_id，可以为 None

    """
    _trace_id_var.set(trace_id)


def bind_trace_id(trace_id: str | None) -> Token:
    """Bind trace_id to the current context and return a reset token."""
    return _trace_id_var.set(trace_id)


def reset_trace_id(token: Token) -> None:
    """Reset the trace_id context to a previous token."""
    _trace_id_var.reset(token)


class TraceContext:
    """Trace Context Manager

    用于在代码块中设置 trace_id，退出时自动恢复原来的值

    Examples:
        # 使用新生成的 trace_id
        with TraceContext():
            logger.info("This log will have a trace_id")

        # 使用指定的 trace_id
        with TraceContext("custom-trace-id"):
            logger.info("This log will have custom-trace-id")

    """

    def __init__(self, trace_id: str | None = None):
        """Args:
        trace_id: 指定的 trace_id，如果为 None 则自动生成

        """
        self.trace_id = trace_id or generate_trace_id()
        self.token = None

    def __enter__(self):
        self.token = _trace_id_var.set(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        _trace_id_var.reset(self.token)
        return False


def with_trace(trace_id: str | None = None):
    """装饰器：为函数调用添加 trace_id

    Args:
        trace_id: 指定的 trace_id，如果为 None 则自动生成

    Examples:
        @with_trace()
        def my_function():
            logger.info("This will have a trace_id")

        @with_trace("custom-trace-id")
        async def my_async_function():
            logger.info("This will have custom-trace-id")

    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            with TraceContext(trace_id):
                return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            with TraceContext(trace_id):
                return await func(*args, **kwargs)

        # 根据函数类型返回对应的 wrapper
        import inspect
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def format_trace_id(trace_id: str | None) -> str:
    """格式化 trace_id 用于日志输出

    Args:
        trace_id: 原始 trace_id

    Returns:
        格式化后的 trace_id，如果为 None 则返回 "-"

    """
    return trace_id or "-"

