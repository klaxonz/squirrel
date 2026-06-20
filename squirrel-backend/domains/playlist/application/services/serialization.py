from __future__ import annotations

from domains.playlist.domain.models.playlist import Playlist
from domains.playlist.domain.models.playlist_item import PlaylistItem
from domains.playlist.interfaces.dto.playlist_responses import PlaylistItemResponse, PlaylistResponse


def serialize_playlist(playlist: Playlist, video_count: int = 0) -> dict:
    """Serialize a Playlist into its public response shape.

    Uses an explicit Pydantic schema so the response contract is stable;
    ``video_count`` is the aggregated count (not a column) as before.
    """
    data = PlaylistResponse.model_validate(playlist).model_dump()
    data['video_count'] = video_count
    return data


def serialize_item(item: PlaylistItem) -> dict:
    """Serialize a PlaylistItem into its public response shape."""
    return PlaylistItemResponse.model_validate(item).model_dump()
