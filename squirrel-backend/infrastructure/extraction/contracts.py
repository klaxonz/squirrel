"""Backend-owned extraction contracts.

The extraction task/result wrappers are canonical in ``sites.crawl.core`` (the
site boundary contract — deliberately dependency-free, stdlib only). The
backend pipeline re-exports them here and adds pipeline-only concerns:
``TaskStatus`` (scheduling enum) and the ``Extractor`` protocol.

The one thing the pipeline adds on top of the site result is its data payload:
sites carry a minimal ``VideoMeta``, the pipeline persists ``RuntimeVideoData``.
``site_result_to_extraction_result`` is the single explicit conversion for that
step — no dict round-trips.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol, runtime_checkable

from sites.crawl import ExtractionResult, ExtractionTask, TaskPriority, VideoMeta

from .runtime_payloads import RuntimeVideoData

__all__ = [
    'TaskStatus',
    'TaskPriority',
    'ExtractionResult',
    'ExtractionTask',
    'Extractor',
    'site_result_to_extraction_result',
]


class TaskStatus(StrEnum):
    """Execution status of an extraction task."""

    PENDING = 'pending'
    PROCESSING = 'processing'
    COMPLETED = 'completed'
    FAILED = 'failed'
    CANCELLED = 'cancelled'


@runtime_checkable
class Extractor(Protocol):
    """Backend extractor protocol."""

    site_name: str
    supported_domains: list[str]

    def can_handle(self, url: str) -> bool: ...

    def extract(self, task: ExtractionTask) -> ExtractionResult: ...

    def validate_url(self, url: str) -> bool: ...


def site_result_to_extraction_result(result: ExtractionResult) -> ExtractionResult:
    """Convert a site runtime extraction result into a pipeline result.

    Both layers share the ``ExtractionResult`` wrapper; this converts the data
    payload (site ``VideoMeta`` -> pipeline ``RuntimeVideoData``) losslessly
    and copies failure fields (``error``, ``error_category``, ``retryable``,
    ``error_context``) exactly.

    Raises:
        TypeError: success result whose data is not a VideoMeta.
    """
    if not result.success:
        return ExtractionResult(
            success=False,
            error=result.error,
            error_category=result.error_category,
            retryable=result.retryable,
            error_context=dict(result.error_context) if result.error_context else None,
        )

    if not isinstance(result.data, VideoMeta):
        raise TypeError(
            f'Site extraction success result must carry VideoMeta, got '
            f'{type(result.data).__name__ if result.data is not None else "None"}'
        )
    return ExtractionResult(
        success=True,
        data=RuntimeVideoData.from_dict(result.data.to_dict()),
    )
