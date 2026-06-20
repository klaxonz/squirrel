"""Pydantic response schemas for video clip markers.

Replaces ``VideoClipMarker.to_dict()`` in the marker serialization path with
an explicit field set; adding a column to the model can no longer leak into
API responses.
"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from infrastructure.http.serializers import serialize_datetime


class ClipMarkerResponse(BaseModel):
    """A single video clip marker as returned by the marker CRUD endpoints."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    video_id: int
    title: str | None = None
    note: str | None = None
    preview_image_url: str | None = None
    start_time: float
    end_time: float
    duration_seconds: float = 0.0
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_serializer('created_at', 'updated_at')
    def _serialize_datetime(self, dt: datetime | None) -> str | None:
        return serialize_datetime(dt)
