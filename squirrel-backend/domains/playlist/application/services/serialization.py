from __future__ import annotations

from domains.playlist.domain.models.playlist import Playlist
from domains.playlist.domain.models.playlist_item import PlaylistItem


def serialize_playlist(playlist: Playlist, video_count: int = 0) -> dict:
    payload = playlist.to_dict()
    payload['video_count'] = video_count
    return payload


def serialize_item(item: PlaylistItem) -> dict:
    return item.to_dict()
