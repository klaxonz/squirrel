from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import format_image_url


def normalize_mv(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('id') or row.get('video_id') or row.get('mv_id') or ''),
        'name': str(row.get('name') or row.get('title') or row.get('filename') or ''),
        'hash': str(row.get('hash') or row.get('mv_hash') or row.get('FileHash') or ''),
        'cover': format_image_url(row.get('cover') or row.get('img') or row.get('imgurl') or ''),
        'duration': int(row.get('duration') or row.get('time_length') or 0),
    }


def normalize_video(row: dict[str, Any]) -> dict[str, Any]:
    authors = row.get('authors') if isinstance(row.get('authors'), list) else []
    author_name = ''
    for author in authors:
        if isinstance(author, dict):
            name = author.get('author_name') or author.get('name')
            if name:
                author_name = name
                break
    return {
        'id': str(row.get('id') or row.get('video_id') or row.get('mv_id') or ''),
        'name': str(row.get('name') or row.get('title') or row.get('filename') or ''),
        'cover': format_image_url(
            row.get('cover') or row.get('img') or row.get('imgurl') or row.get('cover_url') or ''
        ),
        'duration': int(row.get('duration') or row.get('time_length') or 0),
        'play_count': int(row.get('play_count') or row.get('playcount') or 0),
        'artist': author_name or str(row.get('author_name') or row.get('singer_name') or ''),
        'artist_id': str(row.get('author_id') or row.get('singer_id') or ''),
    }
