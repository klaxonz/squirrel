"""Library: playlists (public & user), history, favorites, related songs."""

from typing import Any

from schemas.music import MusicTrackPayload
from services.music._client import _request_kugou
from services.music._normalizers import (
    _first_list,
    _normalize_playlist,
    _normalize_playlist_tags,
    _normalize_track,
    _normalize_user_playlist,
)


def _playlist_track_data(track: MusicTrackPayload) -> str:
    return '|'.join([track.title, track.hash, track.album_id, track.album_audio_id])


async def list_playlists(user_id: int, category_id: int, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/top/playlist', {
        'category_id': category_id,
        'page': page,
        'pagesize': page_size,
        'withsong': 0,
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('special_list')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_playlist(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'has_more': bool(data.get('has_next')),
    }


async def list_playlist_tags(user_id: int) -> dict[str, Any]:
    payload = await _request_kugou('/playlist/tags', {}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('info', 'list', 'tags', 'data'))
    return {
        'items': _normalize_playlist_tags(rows),
    }


async def get_similar_playlists(user_id: int, playlist_id: str) -> dict[str, Any]:
    payload = await _request_kugou('/playlist/similar', {'ids': playlist_id}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('info', 'list', 'lists', 'special_list', 'data'))
    return {
        'items': [_normalize_playlist(row) for row in rows],
    }


async def get_playlist_tracks(user_id: int, playlist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/playlist/track/all', {
        'id': playlist_id,
        'page': page,
        'pagesize': page_size,
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('songs')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': data.get('count') or len(rows),
    }


async def list_user_playlists(user_id: int, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/user/playlist', {
        'page': page,
        'pagesize': page_size,
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('info', 'lists', 'list', 'data'))
    if isinstance(data, dict):
        total = data.get('total') or data.get('count') or len(rows)
    else:
        total = len(rows)

    return {
        'items': [_normalize_user_playlist(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': total,
    }


async def get_user_playlist_tracks(user_id: int, list_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/playlist/track/all/new', {
        'listid': list_id,
        'page': page,
        'pagesize': page_size,
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('info', 'songs', 'list', 'files', 'data'))
    if isinstance(data, dict):
        total = data.get('total') or data.get('count') or len(rows)
    else:
        total = len(rows)

    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': total,
    }


async def create_user_playlist(user_id: int, name: str, is_private: bool) -> dict[str, Any]:
    await _request_kugou('/playlist/add', {
        'name': name,
        'type': 0,
        'is_pri': 1 if is_private else 0,
    }, user_id=user_id)
    return {'ok': True}


async def collect_playlist(user_id: int, playlist_id: str) -> dict[str, Any]:
    from services.music._client import MusicServiceError
    detail_payload = await _request_kugou('/playlist/detail', {'ids': playlist_id}, user_id=user_id)
    detail_rows = detail_payload.get('data') if isinstance(detail_payload.get('data'), list) else []
    detail = detail_rows[0] if detail_rows and isinstance(detail_rows[0], dict) else {}
    list_create_userid = str(detail.get('list_create_userid') or '')
    list_create_listid = str(detail.get('list_create_listid') or '')
    name = str(detail.get('name') or '')
    if not list_create_userid or not list_create_listid or not name:
        raise MusicServiceError('KuGouMusicApi playlist detail missed collect fields')

    await _request_kugou('/playlist/add', {
        'name': name,
        'type': 1,
        'source': detail.get('source') or 1,
        'list_create_userid': list_create_userid,
        'list_create_listid': list_create_listid,
        'list_create_gid': detail.get('list_create_gid') or playlist_id,
    }, user_id=user_id)
    return {'ok': True}


async def delete_user_playlist(user_id: int, list_id: str) -> dict[str, Any]:
    await _request_kugou('/playlist/del', {'listid': list_id}, user_id=user_id)
    return {'ok': True}


async def add_track_to_user_playlist(user_id: int, list_id: str, track: MusicTrackPayload) -> dict[str, Any]:
    await _request_kugou('/playlist/tracks/add', {
        'listid': list_id,
        'data': _playlist_track_data(track),
    }, user_id=user_id)
    return {'ok': True}


async def remove_tracks_from_user_playlist(user_id: int, list_id: str, file_ids: str) -> dict[str, Any]:
    await _request_kugou('/playlist/tracks/del', {
        'listid': list_id,
        'fileids': file_ids,
    }, user_id=user_id)
    return {'ok': True}


async def get_user_history(user_id: int, bp: str | None) -> dict[str, Any]:
    params = {}
    if bp:
        params['bp'] = bp
    payload = await _request_kugou('/user/history', params, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('songs', 'info', 'list', 'data'))
    if isinstance(data, dict):
        bp = data.get('bp') or data.get('next_bp') or ''
    else:
        bp = ''

    return {
        'items': [_normalize_track(row) for row in rows],
        'bp': bp,
    }


async def get_user_listen_rank(user_id: int, history_type: int) -> dict[str, Any]:
    payload = await _request_kugou('/user/listen', {'type': history_type}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('songs', 'info', 'list', 'data'))

    return {
        'items': [_normalize_track(row) for row in rows],
    }


async def get_latest_listen_songs(user_id: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou('/lastest/songs/listen', {'pagesize': page_size}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('songs', 'info', 'list', 'data'))

    return {
        'items': [_normalize_track(row) for row in rows],
    }


async def upload_play_history(user_id: int, album_audio_id: str, played_at: int | None, play_count: int) -> dict[str, Any]:
    params = {
        'mxid': album_audio_id,
        'pc': play_count,
    }
    if played_at:
        params['time'] = played_at
    await _request_kugou('/playhistory/upload', params, user_id=user_id)
    return {'ok': True}


async def get_favorite_counts(user_id: int, mixsongids: str) -> dict[str, Any]:
    payload = await _request_kugou('/favorite/count', {'mixsongids': mixsongids}, user_id=user_id, use_auth=False)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('list') if isinstance(data.get('list'), list) else []
    return {
        'items': [
            {
                'mixsongid': str(row.get('mixsongid') or ''),
                'count': int(row.get('count') or 0),
                'count_text': str(row.get('count_text') or ''),
            }
            for row in rows
            if isinstance(row, dict)
        ],
    }


async def get_related_tracks(
    user_id: int,
    album_audio_id: str,
    page: int,
    page_size: int,
    sort: str,
    type_id: str | None,
) -> dict[str, Any]:
    params: dict[str, Any] = {
        'album_audio_id': album_audio_id,
        'page': page,
        'pagesize': page_size,
        'sort': sort,
    }
    if type_id:
        params['type'] = type_id
    payload = await _request_kugou('/audio/related', params, user_id=user_id, use_auth=False)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('info', 'list', 'lists', 'songs', 'data'))
    if isinstance(data, dict):
        total = data.get('total') or data.get('count') or len(rows)
    else:
        total = len(rows)

    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': total,
    }
