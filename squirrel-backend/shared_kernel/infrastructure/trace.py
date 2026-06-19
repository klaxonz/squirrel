"""Trace tracking utility module

Provides unified trace_id management, supporting cross-thread, coroutine, and message queue trace tracking.

Core features:
- Generate unique trace_id
- Store and retrieve trace_id in context
- Provide decorator and context manager for setting trace_id
"""

import uuid
from contextvars import ContextVar, Token

# Use ContextVar to store trace_id, supports async and thread isolation
_trace_id_var: ContextVar[str | None] = ContextVar('trace_id', default=None)


def generate_trace_id() -> str:
    """Generate a unique trace_id

    Returns:
        32-character hex string (UUID hex representation)

    """
    return uuid.uuid4().hex


def get_trace_id() -> str | None:
    """Get the current context trace_id

    Returns:
        Current trace_id, or None if not set

    """
    return _trace_id_var.get()


def set_trace_id(trace_id: str | None) -> None:
    """Set the current context trace_id

    Args:
        trace_id: trace_id to set, can be None

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

    Sets trace_id within a code block and automatically restores the original value on exit

    Examples:
        # Use a newly generated trace_id
        with TraceContext():
            logger.info("This log will have a trace_id")

        # Use a specified trace_id
        with TraceContext("custom-trace-id"):
            logger.info("This log will have custom-trace-id")

    """

    def __init__(self, trace_id: str | None = None):
        """Args:
        trace_id: Specified trace_id, auto-generated if None

        """
        self.trace_id = trace_id or generate_trace_id()
        self.token = None

    def __enter__(self):
        self.token = _trace_id_var.set(self.trace_id)
        return self.trace_id

    def __exit__(self, exc_type, exc_val, exc_tb):
        _trace_id_var.reset(self.token)
        return False


def format_trace_id(trace_id: str | None) -> str:
    """Format trace_id for log output

    Args:
        trace_id: Raw trace_id

    Returns:
        Formatted trace_id, returns "-" if None

    """
    return trace_id or '-'
