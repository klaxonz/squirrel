from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import first_list


def normalize_hot_search(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'keyword': str(row.get('keyword') or row.get('word') or row.get('name') or row.get('search_word') or ''),
        'score': int(row.get('score') or row.get('hot') or row.get('heat') or 0),
        'jump_url': str(row.get('jump_url') or row.get('url') or ''),
    }


def normalize_suggestion_items(data: Any) -> list[dict[str, Any]]:
    rows = first_list(data, ('info', 'list', 'lists', 'data'))
    if not rows and isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
    return [
        {
            'keyword': str(row.get('keyword') or row.get('HintInfo') or row.get('name') or row.get('SongName') or ''),
            'type': str(row.get('type') or row.get('search_type') or row.get('RecordType') or ''),
        }
        for row in rows
    ]
