"""Backend-local payload models for plugin extraction responses."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class RuntimeActorData:
    url: str
    name: str | None = None
    avatar: str | None = None
    extra_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeActorData:
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
    thumbnail: str | None = None
    duration: int | None = None
    publish_date: Any | None = None
    extra_data: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RuntimeVideoData:
        return cls(
            title=str(data.get('title', '')),
            url=str(data.get('url', '')),
            thumbnail=data.get('thumbnail'),
            duration=data.get('duration'),
            publish_date=data.get('publish_date'),
            extra_data=data.get('extra_data'),
        )
