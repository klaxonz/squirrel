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
class SubscriptionSyncResult:
    video_urls: List[str]
    latest_video_url: Optional[str] = None
    cursor_payload: Optional[Dict[str, Any]] = None
    has_more: bool = False
    stop_reason: Optional[str] = None
    source_video_count: Optional[int] = None
    total_available: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SubscriptionSyncResult':
        return cls(**data)
