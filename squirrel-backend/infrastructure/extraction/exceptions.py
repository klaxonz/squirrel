"""Unified exception hierarchy for the extraction pipeline"""

from datetime import datetime
from typing import Any


class ExtractionError(Exception):
    """Base extraction error

    Provides:
    - Error classification (retryable / non-retryable)
    - Context information
    - Timestamp
    """

    def __init__(
        self,
        message: str,
        retryable: bool = False,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.context = context or {}
        self.timestamp = datetime.now()

    def __str__(self):
        return f'{self.__class__.__name__}: {self.message}'

    def __repr__(self):
        return (
            f"{self.__class__.__name__}(message='{self.message}', retryable={self.retryable}, context={self.context})"
        )


# ========== Data transformation errors ==========


class DataTransformError(ExtractionError):
    """Data transformation error

    Scenarios:
    - Plugin Video object to VideoDTO conversion failure
    - Data format does not meet expectations
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


class ValidationError(ExtractionError):
    """Data validation error

    Scenarios:
    - Invalid URL format
    - Missing required fields
    - Data type mismatch
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


# ========== Network errors (retryable) ==========


class NetworkError(ExtractionError):
    """Network error

    Scenarios:
    - Connection timeout
    - DNS resolution failure
    - Server unresponsive
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


# ========== Business logic errors (non-retryable) ==========


class ResourceNotFoundError(ExtractionError):
    """Resource not found

    Scenarios:
    - Video has been deleted
    - Channel does not exist
    - Page 404
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


class PermissionError(ExtractionError):
    """Permission error

    Scenarios:
    - Login required
    - Region restriction
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


class VipError(ExtractionError):
    """VIP permission error

    Scenarios:
    - VIP membership required
    - Paid subscription required
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=False, **kwargs)


# ========== System errors (retryable) ==========


class DatabaseError(ExtractionError):
    """Database error

    Scenarios:
    - Connection failure
    - Query timeout
    - Transaction failure
    """

    def __init__(self, message: str, **kwargs):
        super().__init__(message, retryable=True, **kwargs)


# ========== Pipeline errors ==========


class PipelineError(ExtractionError):
    """Pipeline execution error

    Scenarios:
    - Stage execution failure
    - Missing context data
    - Pipeline interruption
    """

    def __init__(self, message: str, stage_name: str | None = None, **kwargs):
        super().__init__(message, retryable=False, **kwargs)
        self.stage_name = stage_name


class StageExecutionError(PipelineError):
    """Stage execution error

    More specific Pipeline Stage error
    """
