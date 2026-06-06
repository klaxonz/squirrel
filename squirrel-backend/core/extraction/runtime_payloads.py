"""
Backend-local payload models for plugin extraction responses.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional


@dataclass
class RuntimeActorData:
    url: str
    name: Optional[str] = None
    avatar: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuntimeActorData':
        return cls(
            url=str(data.get('url', '')),
            name=data.get('name'),
            avatar=data.get('avatar'),
            extra_data=data.get('extra_data'),
        )


@dataclass
class RuntimeVideoData:
    title: str
    url: str
    thumbnail: Optional[str] = None
    duration: Optional[int] = None
    publish_date: Optional[Any] = None
    extra_data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RuntimeVideoData':
        return cls(
            title=str(data.get('title', '')),
            url=str(data.get('url', '')),
            thumbnail=data.get('thumbnail'),
            duration=data.get('duration'),
            publish_date=data.get('publish_date'),
            extra_data=data.get('extra_data'),
        )
