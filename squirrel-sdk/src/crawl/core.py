"""Core interfaces & dataclasses for crawl/extraction plugins.

This file is intentionally **dependency-free** (stdlib only) so that
`squirrel-sdk` can be vendored or installed in a variety of runtimes
without pulling heavy third-party libraries.

Design principles:
- Use Protocol for interfaces (structural typing)
- VideoMeta as the primary data model
- Video as optional extension for domain-specific logic
- Composition over inheritance
"""
from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

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
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VideoMeta":
        return cls(**data)


# ---------------- Result / Task -----------------


@dataclass
class ExtractionResult:
    """Outcome of a task (either success or failure).

    The data field must contain VideoMeta. This is the only supported data type.
    """

    success: bool
    data: Optional[VideoMeta] = None
    error: Optional[str] = None
    error_category: Optional[str] = None
    retryable: bool = False
    error_context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Serialize result to dictionary."""
        return {
            "success": self.success,
            "data": self.data.to_dict() if self.data else None,
            "error": self.error,
            "error_category": self.error_category,
            "retryable": self.retryable,
            "error_context": self.error_context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionResult":
        """Deserialize result from dictionary."""
        data_payload = data.get("data")
        if data_payload and isinstance(data_payload, dict):
            data_payload = VideoMeta.from_dict(data_payload)
        elif data_payload and not isinstance(data_payload, VideoMeta):
            data_payload = None

        return cls(
            success=data.get("success", False),
            data=data_payload,
            error=data.get("error"),
            error_category=data.get("error_category"),
            retryable=data.get("retryable", False),
            error_context=data.get("error_context"),
        )

    @classmethod
    def failure(
        cls,
        error: Union[str, Exception],
        context: Optional[Dict[str, Any]] = None
    ) -> "ExtractionResult":
        """Create a failure result from error."""
        from .exceptions import PluginError

        if isinstance(error, PluginError):
            return cls(
                success=False,
                error=error.message,
                error_category=error.category.value,
                retryable=error.retryable,
                error_context={**error.context, **(context or {})}
            )
        return cls(
            success=False,
            error=str(error),
            error_context=context
        )

    @classmethod
    def success_result(cls, data: VideoMeta) -> "ExtractionResult":
        """Create a success result with data."""
        return cls(success=True, data=data)


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


@runtime_checkable
class Extractor(Protocol):
    """Protocol for extractor plugins.
    
    This is a structural interface - any class implementing these methods
    is considered an extractor, regardless of inheritance.
    """
    
    # Class-level metadata (recommended for performance)
    site_name: str
    supported_domains: List[str]
    
    def can_handle(self, url: str) -> bool:
        """Return True if the given URL is supported by this extractor."""
        ...
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """Execute the extraction and return the result."""
        ...
    
    def validate_url(self, url: str) -> bool:
        """Lightweight URL validation prior to queueing the task."""
        ...


@runtime_checkable
class TaskProcessor(Protocol):
    """Protocol for higher-level task processors that orchestrate multiple extractors."""
    
    def process(self, task: ExtractionTask) -> ExtractionResult:
        """Process a task and return the result."""
        ...
    
    def can_process(self, task: ExtractionTask) -> bool:
        """Return True if this processor can handle the task."""
        ...


@runtime_checkable
class ResultHandler(Protocol):
    """Protocol for processing results – store to DB, enqueue messages, etc."""
    
    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """Handle a successful extraction result."""
        ...


# ---------------- Subscription (Channel) -----------------


@dataclass
class SubscriptionSyncContext:
    """Context passed into subscription sync plugins."""

    mode: str
    cursor_payload: Optional[Dict[str, Any]] = None
    last_seen_video_url: Optional[str] = None
    limit: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubscriptionSyncContext":
        return cls(**data)


@dataclass
class SubscriptionSyncResult:
    """Result returned by subscription sync plugins."""

    video_urls: List[str]
    latest_video_url: Optional[str] = None
    cursor_payload: Optional[Dict[str, Any]] = None
    has_more: bool = False
    stop_reason: Optional[str] = None
    source_video_count: Optional[int] = None
    total_available: Optional[int] = None
    head_sample_urls: Optional[List[str]] = None
    anchor_found: Optional[bool] = None
    oldest_scanned_url: Optional[str] = None
    cursor_invalid: Optional[bool] = None
    cursor_loop_detected: Optional[bool] = None
    scan_depth: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubscriptionSyncResult":
        return cls(**data)


@runtime_checkable
class Subscription(Protocol):
    """Protocol for channel/actor subscriptions.
    
    Implementations should be lightweight and rely only on stdlib and the
    SDK's pure-Python utilities. Network and heavy logic should live in the
    plugin package itself.
    """
    
    url: str
    
    def get_subscribe_info(self) -> Any:
        """Return channel metadata; typically a SubscriptionMeta instance."""
        ...
    
    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        """Return cursor-aware sync results for this subscription."""
        ...


@runtime_checkable
class UserSubscriptionImporter(Protocol):
    """Protocol for importing user's subscriptions from a site.
    
    This is used to bulk-import all subscriptions that a user has on a particular
    video site (e.g., all followed channels on Bilibili, all subscribed channels on YouTube).
    """
    
    def get_user_subscriptions(self) -> List[SubscriptionImportItem]:
        """Return a list of subscriptions from the user's account.

        Returns:
            List of subscriptions with metadata (url/name/avatar).

        Note:
            This method should use cookies to authenticate and fetch the user's 
            subscription list. The cookies are resolved via the SDK's cookie    
            configuration.
        """
        ...


@dataclass
class SubscriptionImportBatchResult:
    items: List[SubscriptionImportItem]
    cursor_payload: Optional[Dict[str, Any]] = None
    has_more: bool = False
    stop_reason: Optional[str] = None
    total_available: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'items': [item.to_dict() for item in self.items],
            'cursor_payload': self.cursor_payload,
            'has_more': self.has_more,
            'stop_reason': self.stop_reason,
            'total_available': self.total_available,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionImportBatchResult':
        return cls(
            items=[
                item if isinstance(item, SubscriptionImportItem) else SubscriptionImportItem.from_dict(item)
                for item in list(data.get('items') or [])
            ],
            cursor_payload=dict(data.get('cursor_payload') or {}) or None,
            has_more=bool(data.get('has_more', False)),
            stop_reason=data.get('stop_reason'),
            total_available=data.get('total_available'),
        )


@runtime_checkable
class PaginatedUserSubscriptionImporter(Protocol):
    def get_user_subscriptions_batch(
        self,
        cursor_payload: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
    ) -> SubscriptionImportBatchResult:
        ...




@dataclass
class LoginStatusResult:
    """Result returned by site login status checkers."""

    site_name: str
    logged_in: bool
    username: Optional[str] = None
    user_id: Optional[str] = None
    message: Optional[str] = None
    extra: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_name": self.site_name,
            "logged_in": self.logged_in,
            "username": self.username,
            "user_id": self.user_id,
            "message": self.message,
            "extra": self.extra or {},
        }


# ---------------- Additional Data Models -----------------

@dataclass
class ActorMeta:
    """Data class for actor/channel metadata."""
    url: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ActorMeta":
        return cls(**data)


@dataclass
class SubscriptionImportItem:
    """Subscription item returned by UserSubscriptionImporter."""

    url: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubscriptionImportItem":
        return cls(**data)


@dataclass
class SubscriptionMeta:
    """Subscription metadata for channel/actor information."""
    
    id: str
    name: str
    avatar: Optional[str] = None
    url: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SubscriptionMeta":
        return cls(**data)

