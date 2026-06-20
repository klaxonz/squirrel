"""Pydantic response schemas for the video HTTP boundary.

Replaces ``Video.to_dict()`` / ``Creator.to_dict()`` / ``Subscription.to_dict()``
serialization paths with explicit, whitelisted field sets. Adding a column to
those models can no longer silently leak into API responses.

The video detail / list responses are richer than a plain row -- the loaders
decorate them with aggregated profile data (actors, subscriptions, etc.).
Those decorated payloads are built as plain dicts by the loaders and only the
*base* row serialization is migrated here; the augmentation stays as-is.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class VideoResponse(BaseModel):
    """A Video row's public field set (the contract ``Video.to_dict()`` made).

    Kept broad for parity with the historical behavior so this migration does
    not change wire shape; callers that want a narrower view define their own
    schema on top.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    url: str
    domain: str | None = None
    description: str | None = None
    duration: int | None = None
    thumbnail: str | None = None
    publish_date: datetime | None = None
    is_deleted: bool = False
    extra_data: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer('publish_date', 'created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)


def serialize_video(video) -> dict:
    """Serialize a Video ORM row into its public response shape.

    Centralized so every call site that historically did ``video.to_dict()``
    picks up the same whitelisted schema.
    """
    return VideoResponse.model_validate(video).model_dump()


class CreatorResponse(BaseModel):
    """A Creator row's public field set (the contract ``Creator.to_dict()`` made)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None = None
    url: str
    avatar: str | None = None
    description: str | None = None
    is_deleted: bool = False
    extra_data: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer('created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)


def serialize_creator(creator) -> dict:
    """Serialize a Creator ORM row into its public response shape."""
    return CreatorResponse.model_validate(creator).model_dump()
