from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import format_image_url


def normalize_playlist(row: dict[str, Any]) -> dict[str, Any]:
    tags = row.get('tags')
    if not isinstance(tags, list):
        tags = []

    return {
        'id': str(row.get('global_collection_id') or ''),
        'name': row.get('specialname') or '',
        'cover': format_image_url(row.get('flexible_cover') or row.get('imgurl') or ''),
        'intro': row.get('intro') or '',
        'creator': row.get('nickname') or '',
        'play_count': int(row.get('play_count') or 0),
        'collect_count': int(row.get('collectcount') or 0),
        'tags': [tag.get('tag_name') for tag in tags if isinstance(tag, dict) and tag.get('tag_name')],
        'list_create_userid': str(row.get('list_create_userid') or row.get('suid') or ''),
        'list_create_listid': str(row.get('list_create_listid') or row.get('specialid') or ''),
        'list_create_gid': str(row.get('list_create_gid') or row.get('global_collection_id') or ''),
    }


def normalize_playlist_tags(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tags = []
    for group in rows:
        children = group.get('children') if isinstance(group.get('children'), list) else group.get('tags')
        if not isinstance(children, list):
            children = [group]
        for row in children:
            if not isinstance(row, dict):
                continue
            tag_id = str(row.get('tag_id') or row.get('id') or row.get('category_id') or '')
            name = str(row.get('tag_name') or row.get('name') or row.get('category_name') or '')
            if tag_id and name:
                tags.append({
                    'id': tag_id,
                    'name': name,
                    'parent_id': str(group.get('tag_id') or group.get('id') or ''),
                    'parent_name': str(group.get('tag_name') or group.get('name') or ''),
                })
    return tags


def normalize_user_playlist(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('listid') or row.get('list_id') or row.get('id') or ''),
        'name': row.get('name') or row.get('listname') or row.get('specialname') or '',
        'cover': format_image_url(row.get('pic') or row.get('cover') or row.get('imgurl') or ''),
        'song_count': int(row.get('count') or row.get('song_count') or row.get('filecount') or 0),
        'is_default': bool(row.get('is_default') or row.get('is_def')),
        'is_collected': bool(row.get('is_collected') or row.get('type') == 1),
        'list_create_userid': str(row.get('list_create_userid') or row.get('userid') or ''),
        'list_create_listid': str(row.get('list_create_listid') or row.get('listid') or ''),
        'list_create_gid': str(row.get('list_create_gid') or row.get('gid') or ''),
    }
