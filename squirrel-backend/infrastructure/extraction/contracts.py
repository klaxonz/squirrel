"""Backend-owned extraction contracts.

These types are used by the host extraction pipeline and should not depend on
Shared runtime extractor/task abstractions.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from typing import Any, Protocol, runtime_checkable

from .runtime_payloads import RuntimeVideoData


class TaskStatus(StrEnum):
    """Execution status of an extraction task."""

    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


class TaskPriority(int, Enum):
    """Priority of a task; larger values are more important."""

    NORMAL = 2
    HIGH = 3


@dataclass
class ExtractionResult:
    """Outcome of an extraction task."""

    success: bool
    data: Any | None = None
    error: str | None = None
    error_category: str | None = None
    retryable: bool = False
    error_context: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ExtractionResult:
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
    def success_result(cls, data: Any) -> ExtractionResult:
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
    metadata: dict[str, Any] | None = None

    def __post_init__(self) -> None:
        self.task_id = uuid.uuid5(uuid.NAMESPACE_URL, f'{self.site_name}:{self.url}').hex


@runtime_checkable
class Extractor(Protocol):
    """Backend extractor protocol."""

    site_name: str
    supported_domains: list[str]

    def can_handle(self, url: str) -> bool: ...

    def extract(self, task: ExtractionTask) -> ExtractionResult: ...

    def validate_url(self, url: str) -> bool: ...
