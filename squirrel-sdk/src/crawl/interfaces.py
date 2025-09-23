"""Core interfaces & dataclasses for crawl/extraction plugins.

This file is intentionally **dependency-free** (stdlib only) so that
`squirrel-sdk` can be vendored or installed in a variety of runtimes
without pulling heavy third-party libraries.
"""
from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# Public API of this module is stable – add to __all__ in parent __init__.


class TaskStatus(str, Enum):
    """Execution status of an extraction task."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(int, Enum):
    """Priority of a task – larger means more important."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


# ---------------- Data models -----------------


@dataclass
class VideoMeta:
    """Minimal set of metadata required by squirrel-backend."""

    title: str
    url: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None  # seconds
    publish_date: Optional[Any] = None  # str | int
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoMeta":
        return cls(**data)


# ---------------- Result / Task -----------------


@dataclass
class ExtractionResult:
    """Outcome of a task (either success or failure)."""

    success: bool
    data: Optional[VideoMeta] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    # -------------------- convenience --------------------
    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict

        d = asdict(self)
        if isinstance(self.data, VideoMeta):
            d["data"] = self.data.to_dict()
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionResult":
        if "data" in data and isinstance(data["data"], dict):
            data["data"] = VideoMeta.from_dict(data["data"])
        return cls(**data)


@dataclass
class ExtractionTask:
    """A unit of work for the extractor."""

    url: str
    site_name: str
    task_id: str = field(init=False)
    priority: TaskPriority = TaskPriority.NORMAL
    retry_count: int = 0
    max_retries: int = 3
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:  # noqa: D401 – not a docstring for public API
        # Generate deterministic id from url + site for idempotency within a process
        self.task_id = uuid.uuid5(uuid.NAMESPACE_URL, f"{self.site_name}:{self.url}").hex

    @property
    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    # -------------------- convenience --------------------
    def to_dict(self) -> Dict[str, Any]:
        from dataclasses import asdict

        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionTask":
        return cls(**data)  # type: ignore[arg-type]


class IExtractor(abc.ABC):
    """Base interface every extractor plugin must implement."""

    # Recommended class-level metadata (not strictly required but improves
    # factory performance & static analysis). Subclasses should set these.
    site_name: str  # e.g. "youtube"
    supported_domains: List[str]  # e.g. ["youtube.com", "youtu.be"]

    @property
    def supported_sites(self) -> List[str]:  # noqa: D401 – purposely concise
        """Return list with single ``site_name`` by default."""
        return [self.site_name]

    @abc.abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return *True* if the given URL is supported by this extractor."""

    @abc.abstractmethod
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """Execute the extraction and return the result."""

    @abc.abstractmethod
    def validate_url(self, url: str) -> bool:
        """Lightweight URL validation prior to queueing the task."""


class ITaskProcessor(abc.ABC):
    """A higher-level task processor may orchestrate multiple extractors."""

    @abc.abstractmethod
    def process(self, task: ExtractionTask) -> ExtractionResult:
        ...

    @abc.abstractmethod
    def can_process(self, task: ExtractionTask) -> bool:
        ...


class IResultHandler(abc.ABC):
    """Process results – store to DB, enqueue messages, etc."""

    @abc.abstractmethod
    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        ...

    @abc.abstractmethod
    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        ...
