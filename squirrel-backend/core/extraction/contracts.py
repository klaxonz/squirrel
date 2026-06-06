"""
Backend-owned extraction contracts.

These types are used by the host extraction pipeline and should not depend on
SDK-owned extractor/task abstractions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Protocol, runtime_checkable

from .runtime_payloads import RuntimeVideoData


class TaskStatus(str, Enum):
    """Execution status of an extraction task."""

    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class TaskPriority(int, Enum):
    """Priority of a task; larger values are more important."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class ExtractionResult:
    """Outcome of an extraction task."""

    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    retryable: bool = False
    error_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data.to_dict() if hasattr(self.data, 'to_dict') else self.data,
            'error': self.error,
            'error_category': self.error_category,
            'retryable': self.retryable,
            'error_context': self.error_context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ExtractionResult':
        data_payload = data.get('data')
        if data_payload and isinstance(data_payload, dict):
            data_payload = RuntimeVideoData.from_dict(data_payload)

        return cls(
            success=bool(data.get('success', False)),
            data=data_payload,
            error=data.get('error'),
            error_category=data.get('error_category'),
            retryable=bool(data.get('retryable', False)),
            error_context=data.get('error_context'),
        )

    @classmethod
    def success_result(cls, data: Any) -> 'ExtractionResult':
        return cls(success=True, data=data)


@dataclass
class ExtractionTask:
    """A unit of work for extraction."""

    url: str
    site_name: str
    task_id: str = field(init=False)
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        self.task_id = uuid.uuid5(uuid.NAMESPACE_URL, f'{self.site_name}:{self.url}').hex

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def to_dict(self) -> Dict[str, Any]:
        return {
            'url': self.url,
            'site_name': self.site_name,
            'task_id': self.task_id,
            'priority': self.priority,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries,
            'metadata': self.metadata,
        }


@runtime_checkable
class Extractor(Protocol):
    """Backend extractor protocol."""

    site_name: str
    supported_domains: list[str]

    def can_handle(self, url: str) -> bool:
        ...

    def extract(self, task: ExtractionTask) -> ExtractionResult:
        ...

    def validate_url(self, url: str) -> bool:
        ...


@runtime_checkable
class TaskProcessor(Protocol):
    """Higher-level processor that can execute extraction tasks."""

    def process(self, task: ExtractionTask) -> ExtractionResult:
        ...

    def can_process(self, task: ExtractionTask) -> bool:
        ...


@runtime_checkable
class ResultHandler(Protocol):
    """Protocol for extraction result handling."""

    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        ...

    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        ...
