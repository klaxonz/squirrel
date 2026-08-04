"""Unified runtime helper exception system.

Provides site-layer exception classes with error categorization, retry decision support, and context passing.
"""
from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):  # noqa: UP042
    """Error category for determining retry behavior and error display."""
    NETWORK = "network"
    RATE_LIMIT = "rate_limit"
    AUTH = "auth"
    VIP = "vip"
    NOT_FOUND = "not_found"
    PARSE = "parse"
    UNKNOWN = "unknown"


class SiteError(Exception):
    """Base class for site errors."""

    def __init__(
        self,
        message: str,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        retryable: bool = False,
        context: dict[str, Any] | None = None
    ):
        super().__init__(message)
        self.message = message
        self.category = category
        self.retryable = retryable
        self.context = context or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "message": self.message,
            "category": self.category.value,
            "retryable": self.retryable,
            "context": self.context
        }

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.message!r}, category={self.category.value})"


class NetworkError(SiteError):
    """Network error (connection timeout, DNS failure, etc.), retryable."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, ErrorCategory.NETWORK, retryable=True, context=context)


class RateLimitError(SiteError):
    """Rate limit error, retryable (after a delay)."""

    def __init__(
        self,
        message: str,
        retry_after: int = 60,
        context: dict[str, Any] | None = None
    ):
        super().__init__(message, ErrorCategory.RATE_LIMIT, retryable=True, context=context)
        self.retry_after = retry_after


class AuthError(SiteError):
    """Authentication error (login required), non-retryable."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, ErrorCategory.AUTH, retryable=False, context=context)


class VipError(SiteError):
    """VIP permission error (VIP subscription required), non-retryable."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, ErrorCategory.VIP, retryable=False, context=context)


class NotFoundError(SiteError):
    """Resource not found (video deleted, 404, etc.), non-retryable."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, ErrorCategory.NOT_FOUND, retryable=False, context=context)


class ParseError(SiteError):
    """Parse error (page structure changed, data format error, etc.), non-retryable."""

    def __init__(self, message: str, context: dict[str, Any] | None = None):
        super().__init__(message, ErrorCategory.PARSE, retryable=False, context=context)
