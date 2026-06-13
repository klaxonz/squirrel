from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import artist_id, artist_names, format_image_url


def normalize_album(row: dict[str, Any]) -> dict[str, Any]:
    authors = row.get('authors') if isinstance(row.get('authors'), list) else []
    first_author = next((item for item in authors if isinstance(item, dict)), {})
    album_id = str(row.get('album_id') or row.get('albumid') or '')
    album_name = row.get('album_name') or row.get('albumname') or ''
    cover = row.get('sizable_cover') or row.get('imgurl') or ''
    artist = row.get('author_name') or row.get('singername') or first_author.get('author_name') or ''
    current_artist_id = str(row.get('singerid') or first_author.get('author_id') or '')
    publish_date = row.get('publish_date') or row.get('publishtime') or ''

    return {
        'id': album_id,
        'name': album_name,
        'cover': format_image_url(cover),
        'intro': row.get('intro') or '',
        'artist': artist,
        'artist_id': current_artist_id,
        'publish_date': publish_date.split()[0] if publish_date else '',
        'language': row.get('language') or '',
        'type': row.get('type') or '',
        'heat': int(row.get('heat') or 0),
    }


def normalize_album_from_track(row: dict[str, Any]) -> dict[str, Any]:
    album_info = row.get('album_info') if isinstance(row.get('album_info'), dict) else {}
    album_id = str(row.get('AlbumID') or row.get('album_id') or '')
    album_name = row.get('AlbumName') or album_info.get('album_name') or row.get('album_name') or ''
    current_artist_id = artist_id(row)
    return {
        'id': album_id,
        'name': album_name,
        'cover': format_image_url(row.get('Image') or row.get('cover') or album_info.get('sizable_cover') or ''),
        'intro': '',
        'artist': row.get('SingerName') or row.get('author_name') or artist_names(row),
        'artist_id': current_artist_id,
        'publish_date': '',
        'language': '',
        'type': '',
        'heat': 0,
    }
