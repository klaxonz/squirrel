from __future__ import annotations

from typing import Any


def format_image_url(value: str) -> str:
    return value.replace('{size}', '240') if value else ''


def milliseconds_to_seconds(value: Any) -> int:
    try:
        milliseconds = int(value or 0)
    except (TypeError, ValueError):
        return 0
    if milliseconds > 1000:
        return round(milliseconds / 1000)
    return milliseconds


def artist_names(row: dict[str, Any]) -> str:
    for key in ('authors', 'singerinfo'):
        rows = row.get(key)
        if isinstance(rows, list):
            names = []
            for item in rows:
                if isinstance(item, dict):
                    name = item.get('author_name') or item.get('name')
                    if name:
                        names.append(name)
            if names:
                return '、'.join(names)
    return ''


def artist_id(row: dict[str, Any]) -> str:
    for key in ('SingerId', 'author_id', 'singerid'):
        if row.get(key):
            return str(row.get(key))
    for key in ('authors', 'singerinfo'):
        rows = row.get(key)
        if isinstance(rows, list):
            for item in rows:
                if isinstance(item, dict) and (item.get('author_id') or item.get('id')):
                    return str(item.get('author_id') or item.get('id'))
    return ''


def first_list(data: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []
