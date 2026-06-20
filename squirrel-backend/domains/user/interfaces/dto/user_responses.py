"""Pydantic response schemas for the user domain HTTP boundary.

These replace the ORM ``User.to_dict()`` serialization path with an explicit,
whitelisted field set so adding a column to the ``User`` model can never
accidentally leak into API responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class UserResponse(BaseModel):
    """Public user profile as returned by login / /me endpoints.

    Intentionally excludes ``token_version`` and any other sensitive column.
    Mirrors the historical ``User.to_dict(exclude={'token_version'})`` shape.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    avatar: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer('created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)
