"""Backend-local runtime payload models for subscription-related plugin responses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class SubscriptionImportItem:
    url: str
    name: str | None = None
    avatar: str | None = None
    extra_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubscriptionImportItem:
        return cls(**data)


@dataclass
class SubscriptionMeta:
    id: str
    name: str
    avatar: str | None = None
    url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubscriptionMeta:
        return cls(**data)


@dataclass
class SubscriptionImportBatchResult:
    items: list[SubscriptionImportItem]
    cursor_payload: dict[str, Any] | None = None
    has_more: bool = False
    stop_reason: str | None = None
    total_available: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "items": [item.to_dict() for item in self.items],
            "cursor_payload": self.cursor_payload,
            "has_more": self.has_more,
            "stop_reason": self.stop_reason,
            "total_available": self.total_available,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubscriptionImportBatchResult:
        return cls(
            items=[
                item if isinstance(item, SubscriptionImportItem) else SubscriptionImportItem.from_dict(item)
                for item in list(data.get("items") or [])
            ],
            cursor_payload=dict(data.get("cursor_payload") or {}) or None,
            has_more=bool(data.get("has_more", False)),
            stop_reason=data.get("stop_reason"),
            total_available=data.get("total_available"),
        )


@dataclass
class SubscriptionSyncResult:
    video_urls: list[str]
    latest_video_url: str | None = None
    cursor_payload: dict[str, Any] | None = None
    has_more: bool = False
    stop_reason: str | None = None
    source_video_count: int | None = None
    total_available: int | None = None
    head_sample_urls: list[str] | None = None
    anchor_found: bool | None = None
    oldest_scanned_url: str | None = None
    cursor_invalid: bool | None = None
    cursor_loop_detected: bool | None = None
    scan_depth: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SubscriptionSyncResult:
        return cls(**data)
