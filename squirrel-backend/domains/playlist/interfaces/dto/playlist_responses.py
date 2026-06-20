"""Pydantic response schemas for the playlist HTTP boundary.

Replace ``Playlist.to_dict()`` / ``PlaylistItem.to_dict()`` with explicit
field sets so model column additions cannot leak into API responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class PlaylistResponse(BaseModel):
    """A playlist row as returned by playlist list/detail endpoints.

    Includes the computed ``video_count`` (not a column -- aggregated by the
    query layer) that callers historically expected from ``serialize_playlist``.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    description: str | None = None
    is_default: bool = False
    created_at: datetime | None = None
    updated_at: datetime | None = None
    video_count: int = 0

    @field_serializer('created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)


class PlaylistItemResponse(BaseModel):
    """A playlist item row as returned by playlist item endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    playlist_id: int
    user_id: int
    video_id: int
    position: int = 0
    added_at: datetime | None = None

    @field_serializer('added_at')
    def _serialize_added_at(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)
