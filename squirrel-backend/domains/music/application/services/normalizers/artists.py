from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import format_image_url


def normalize_artist(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('author_id') or ''),
        'name': row.get('author_name') or '',
        'avatar': format_image_url(row.get('sizable_avatar') or ''),
        'intro': row.get('intro') or '',
        'song_count': int(row.get('song_count') or 0),
        'album_count': int(row.get('album_count') or 0),
        'fan_count': int(row.get('fansnums') or 0),
    }


def normalize_artist_search(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('AuthorId') or row.get('author_id') or ''),
        'name': row.get('AuthorName') or row.get('author_name') or '',
        'avatar': format_image_url(row.get('Avatar') or row.get('sizable_avatar') or ''),
        'intro': row.get('Auxiliary') or row.get('intro') or '',
        'song_count': int(row.get('AudioCount') or row.get('song_count') or 0),
        'album_count': int(row.get('AlbumCount') or row.get('album_count') or 0),
        'fan_count': int(row.get('FansNum') or row.get('fansnums') or 0),
    }
