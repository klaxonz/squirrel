"""
Backend-local runtime payload models for subscription-related plugin responses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class SubscriptionImportItem:
    url: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionImportItem':
        return cls(**data)


@dataclass
class SubscriptionMeta:
    id: str
    name: str
    avatar: Optional[str] = None
    url: str = ''

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionMeta':
        return cls(**data)


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


@dataclass
class SubscriptionSyncResult:
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
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionSyncResult':
        return cls(**data)
