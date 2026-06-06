"""Search-related music service functions."""

from typing import Any

from services.music._client import _request_kugou
from services.music._normalizers import (
    _normalize_album_from_track,
    _normalize_hot_search,
    _normalize_suggestion_items,
    _normalize_track,
)


async def search_tracks(user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/search', {
        'keywords': query,
        'page': page,
        'pagesize': page_size,
        'type': 'song',
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('lists')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': data.get('total') or data.get('total_count') or len(rows),
    }


async def search_artists(user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
    from services.music._normalizers import _normalize_artist_search
    payload = await _request_kugou('/search', {
        'keywords': query,
        'page': page,
        'pagesize': page_size,
        'type': 'author',
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('lists')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_artist_search(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': data.get('total') or len(rows),
    }


async def search_albums(user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/search', {
        'keywords': query,
        'page': page,
        'pagesize': min(page_size * 3, 50),
        'type': 'song',
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('lists')
    if not isinstance(rows, list):
        rows = []

    albums: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        album = _normalize_album_from_track(row)
        if not album['id'] or album['id'] in seen:
            continue
        seen.add(album['id'])
        albums.append(album)
        if len(albums) >= page_size:
            break

    return {
        'items': albums,
        'page': page,
        'page_size': page_size,
        'total': len(albums),
    }


async def get_default_search_keyword(user_id: int) -> dict[str, Any]:
    payload = await _request_kugou('/search/default', {}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    keyword = ''
    if isinstance(data, dict):
        keyword = str(data.get('keyword') or data.get('show_keyword') or data.get('word') or '')
    return {
        'keyword': keyword,
    }


async def list_hot_searches(user_id: int) -> dict[str, Any]:
    from services.music._normalizers import _first_list

    payload = await _request_kugou('/search/hot', {}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('info', 'list', 'lists', 'items', 'data'))

    return {
        'items': [_normalize_hot_search(row) for row in rows],
    }


async def search_suggestions(user_id: int, query: str) -> dict[str, Any]:
    payload = await _request_kugou('/search/suggest', {
        'keywords': query,
        'albumTipCount': 6,
        'correctTipCount': 6,
        'mvTipCount': 6,
        'musicTipCount': 10,
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload

    return {
        'items': _normalize_suggestion_items(data),
    }
