"""Pydantic response schemas for the subscription HTTP boundary.

Replaces ``Subscription.to_dict()`` with an explicit, whitelisted field set.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class SubscriptionResponse(BaseModel):
    """A Subscription row's public field set.

    ``total_extract`` / ``total_videos`` / ``is_nsfw`` are augmentation fields
    that loaders attach (computed per-video and from the user's
    UserSubscription row); they are NOT model columns but are part of the
    response contract the video-detail endpoint historically produced.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    name: str
    url: str | None = None
    avatar: str | None = None
    description: str | None = None
    total_videos: int = 0
    is_deleted: bool = False
    extra_data: dict[str, Any] | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer('created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)


def serialize_subscription(subscription) -> dict:
    """Serialize a Subscription ORM row into its public response shape."""
    return SubscriptionResponse.model_validate(subscription).model_dump()
