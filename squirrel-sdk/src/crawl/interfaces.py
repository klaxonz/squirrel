"""Core interfaces & dataclasses for crawl/extraction plugins.

This file is intentionally **dependency-free** (stdlib only) so that
`squirrel-sdk` can be vendored or installed in a variety of runtimes
without pulling heavy third-party libraries.
"""
from __future__ import annotations

import abc
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

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


# VideoData = Union[VideoMeta, "Video", Dict[str, Any]]  # 废弃Union设计
# 统一使用Video类型，通过VideoFactory创建具体的Video子类实例


@dataclass
class ExtractionResult:
    """Outcome of a task (either success or failure)."""

    success: bool
    data: Optional[Video] = None  # 现在可以直接使用Video类型
    error: Optional[str] = None

    # -------------------- convenience --------------------
    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "success": self.success,
            "data": None,
            "error": self.error,
        }

        data_obj = self.data
        if data_obj is None:
            payload["data"] = None
        elif hasattr(data_obj, "to_dict") and callable(getattr(data_obj, "to_dict")):
            payload["data"] = data_obj.to_dict()
        elif hasattr(data_obj, "__dict__"):
            payload["data"] = dict(data_obj.__dict__)
        else:
            payload["data"] = data_obj

        return payload

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExtractionResult":
        data_payload = data.get("data")

        # 注意：这里简化处理，因为现在统一使用Video类型
        # Video实例的序列化/反序列化应该由具体的Video子类处理
        return cls(
            success=data.get("success", False),
            data=data_payload,  # Video对象的重建需要更复杂的逻辑
            error=data.get("error"),
        )


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


# ---------------- Subscription (Channel) -----------------


class ISubscription(abc.ABC):
    """Interface for channel/actor subscriptions.

    Implementations should be lightweight and rely only on stdlib and the
    SDK's pure-Python utilities. Network and heavy logic should live in the
    plugin package itself.
    """

    url: str

    def __init__(self, url: str) -> None:
        self.url = url

    @abc.abstractmethod
    def get_subscribe_info(self) -> Any:
        """Return channel metadata; typically a SubscriptionMeta instance."""

    @abc.abstractmethod
    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        """Return a list of video URLs to extract for this subscription."""


class IUserSubscriptionImporter(abc.ABC):
    """Interface for importing user's subscriptions from a site.
    
    This is used to bulk-import all subscriptions that a user has on a particular
    video site (e.g., all followed channels on Bilibili, all subscribed channels on YouTube).
    """

    @abc.abstractmethod
    def get_user_subscriptions(self) -> List[str]:
        """Return a list of subscription URLs from the user's account.
        
        Returns:
            List of subscription URLs (e.g., channel URLs, playlist URLs)
            
        Note:
            This method should use cookies to authenticate and fetch the user's
            subscription list. The cookies are resolved via the SDK's cookie
            configuration.
        """


# ---------------- Video & Actor Base Classes -----------------


class Video:
    """Base class for video metadata"""
    DOMAIN = None

    def __init__(self, url, base_info=None):
        self._url = url
        self._base_info = base_info or {}
        self._id = None
        self._title = None
        self._description = None
        self._tags = None
        self._duration = None
        self._thumbnail = None
        self._upload_date = None
        self._publish_date = None
        self._actors = []
        self._season = None

    @property
    def url(self):
        return self._url

    @property
    def title(self):
        if self._title is None:
            self._title = self._base_info.get("title")
        return self._title

    @property
    def description(self):
        if self._description is None:
            self._description = self._base_info.get("description")
        return self._description

    @property
    def thumbnail(self):
        if self._thumbnail is None:
            self._thumbnail = self._base_info.get("thumbnail")
        return self._thumbnail

    @property
    def upload_date(self):
        if self._upload_date is None:
            self._upload_date = self._base_info.get("upload_date")
        return self._upload_date

    @property
    def publish_date(self):
        if self._publish_date is None:
            self._publish_date = self._base_info.get("publish_date")
        return self._publish_date

    @property
    def tags(self):
        if self._tags is None:
            self._tags = self._base_info.get("tags")
        return self._tags

    @property
    def duration(self):
        if self._duration is None:
            self._duration = self._base_info.get("duration")
        return self._duration

    @property
    def season(self):
        if self._season is None:
            self._season = self.upload_date[0:4]
        return self._season

    @property
    @abc.abstractmethod
    def actors(self):
        """
        Abstract property that must be implemented by subclasses.
        Returns the actors configuration.
        """
        raise NotImplementedError("Subclasses must implement actors property")

    def video_exists(self):
        return True


class Actor:
    """Base class for channel/uploader metadata"""
    DOMAIN = None

    def __init__(self, url):
        self._url = url
        self._name = None
        self._avatar = None

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value

    @property
    def avatar(self):
        return self._avatar

    @avatar.setter
    def avatar(self, value):
        self._avatar = value
