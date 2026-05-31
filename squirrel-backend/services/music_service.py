from typing import Any
from urllib.parse import urljoin

import httpx

from core.cache import redis_client
from core.config import settings
from schemas.music import MusicTrackPayload


class MusicServiceError(Exception):
    pass


KUGOU_AUTH_REDIS_KEY_PREFIX = 'music:kugou:auth'


def search_tracks(user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/search', {
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


def search_artists(user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/search', {
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


def search_albums(user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/search', {
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


def get_personal_fm_tracks(user_id: int) -> dict[str, Any]:
    payload = _request_kugou('/personal/fm', {}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('song_list')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_track(row) for row in rows],
        'page': 1,
        'page_size': len(rows),
        'total': len(rows),
    }


def list_ranks(user_id: int) -> dict[str, Any]:
    payload = _request_kugou('/rank/list', {'withsong': 0}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('info')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_rank(row) for row in rows],
        'total': data.get('total') or len(rows),
    }


def get_rank_tracks(user_id: int, rank_id: str, rank_cid: str | None, page: int, page_size: int) -> dict[str, Any]:
    params = {
        'rankid': rank_id,
        'page': page,
        'pagesize': page_size,
    }
    if rank_cid:
        params['rank_cid'] = rank_cid

    payload = _request_kugou('/rank/audio', params, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('songlist')
    if not isinstance(rows, list):
        rows = []

    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': data.get('total') or payload.get('total') or len(rows),
    }


def list_playlists(user_id: int, category_id: int, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/top/playlist', {
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


def get_playlist_tracks(user_id: int, playlist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/playlist/track/all', {
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


def list_user_playlists(user_id: int, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/user/playlist', {
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
        'raw': payload,
    }


def get_user_playlist_tracks(user_id: int, list_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/playlist/track/all/new', {
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
        'raw': payload,
    }


def get_artist_detail(user_id: int, artist_id: str) -> dict[str, Any]:
    payload = _request_kugou('/artist/detail', {'id': artist_id}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    return _normalize_artist(data)


def get_artist_tracks(user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/artist/audios', {
        'id': artist_id,
        'page': page,
        'pagesize': page_size,
    }, user_id=user_id)
    rows = payload.get('data') if isinstance(payload.get('data'), list) else []
    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': payload.get('total') or len(rows),
    }


def get_artist_albums(user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/artist/albums', {
        'id': artist_id,
        'page': page,
        'pagesize': page_size,
    }, user_id=user_id)
    rows = payload.get('data') if isinstance(payload.get('data'), list) else []
    return {
        'items': [_normalize_album(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': payload.get('total') or len(rows),
    }


def get_album_detail(user_id: int, album_id: str) -> dict[str, Any]:
    payload = _request_kugou('/album/detail', {'id': album_id}, user_id=user_id)
    rows = payload.get('data') if isinstance(payload.get('data'), list) else []
    row = rows[0] if rows and isinstance(rows[0], dict) else {}
    return _normalize_album(row)


def get_album_tracks(user_id: int, album_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/album/songs', {
        'id': album_id,
        'page': page,
        'pagesize': page_size,
    }, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    rows = data.get('songs') if isinstance(data.get('songs'), list) else []
    return {
        'items': [_normalize_track(row) for row in rows],
        'page': page,
        'page_size': page_size,
        'total': data.get('total') or payload.get('total') or len(rows),
    }


def create_user_playlist(user_id: int, name: str, is_private: bool) -> dict[str, Any]:
    payload = _request_kugou('/playlist/add', {
        'name': name,
        'type': 0,
        'is_pri': 1 if is_private else 0,
    }, user_id=user_id)
    return {'ok': True, 'raw': payload}


def collect_playlist(user_id: int, playlist_id: str) -> dict[str, Any]:
    detail_payload = _request_kugou('/playlist/detail', {'ids': playlist_id}, user_id=user_id)
    detail_rows = detail_payload.get('data') if isinstance(detail_payload.get('data'), list) else []
    detail = detail_rows[0] if detail_rows and isinstance(detail_rows[0], dict) else {}
    list_create_userid = str(detail.get('list_create_userid') or '')
    list_create_listid = str(detail.get('list_create_listid') or '')
    name = str(detail.get('name') or '')
    if not list_create_userid or not list_create_listid or not name:
        raise MusicServiceError('KuGouMusicApi playlist detail missed collect fields')

    payload = _request_kugou('/playlist/add', {
        'name': name,
        'type': 1,
        'source': detail.get('source') or 1,
        'list_create_userid': list_create_userid,
        'list_create_listid': list_create_listid,
        'list_create_gid': detail.get('list_create_gid') or playlist_id,
    }, user_id=user_id)
    return {'ok': True, 'raw': payload}


def delete_user_playlist(user_id: int, list_id: str) -> dict[str, Any]:
    payload = _request_kugou('/playlist/del', {'listid': list_id}, user_id=user_id)
    return {'ok': True, 'raw': payload}


def add_track_to_user_playlist(user_id: int, list_id: str, track: MusicTrackPayload) -> dict[str, Any]:
    payload = _request_kugou('/playlist/tracks/add', {
        'listid': list_id,
        'data': _playlist_track_data(track),
    }, user_id=user_id)
    return {'ok': True, 'raw': payload}


def remove_tracks_from_user_playlist(user_id: int, list_id: str, file_ids: str) -> dict[str, Any]:
    payload = _request_kugou('/playlist/tracks/del', {
        'listid': list_id,
        'fileids': file_ids,
    }, user_id=user_id)
    return {'ok': True, 'raw': payload}


def get_user_history(user_id: int, bp: str | None) -> dict[str, Any]:
    params = {}
    if bp:
        params['bp'] = bp
    payload = _request_kugou('/user/history', params, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('songs', 'info', 'list', 'data'))
    if isinstance(data, dict):
        bp = data.get('bp') or data.get('next_bp') or ''
    else:
        bp = ''

    return {
        'items': [_normalize_track(row) for row in rows],
        'bp': bp,
        'raw': payload,
    }


def get_user_listen_rank(user_id: int, history_type: int) -> dict[str, Any]:
    payload = _request_kugou('/user/listen', {'type': history_type}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('songs', 'info', 'list', 'data'))

    return {
        'items': [_normalize_track(row) for row in rows],
        'raw': payload,
    }


def get_latest_listen_songs(user_id: int, page_size: int) -> dict[str, Any]:
    payload = _request_kugou('/lastest/songs/listen', {'pagesize': page_size}, user_id=user_id)
    data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
    rows = _first_list(data, ('songs', 'info', 'list', 'data'))

    return {
        'items': [_normalize_track(row) for row in rows],
        'raw': payload,
    }


def upload_play_history(user_id: int, album_audio_id: str, played_at: int | None, play_count: int) -> dict[str, Any]:
    params = {
        'mxid': album_audio_id,
        'pc': play_count,
    }
    if played_at:
        params['time'] = played_at
    payload = _request_kugou('/playhistory/upload', params, user_id=user_id)
    return {'ok': True, 'raw': payload}


def get_favorite_counts(user_id: int, mixsongids: str) -> dict[str, Any]:
    payload = _request_kugou('/favorite/count', {'mixsongids': mixsongids}, user_id=user_id, use_auth=False)
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
        'raw': payload,
    }


def get_track_play_url(user_id: int, hash_value: str, album_audio_id: str | None, quality: str) -> dict[str, Any]:
    params = {
        'hash': hash_value,
        'quality': quality,
    }
    if album_audio_id:
        params['album_audio_id'] = album_audio_id

    payload = _request_kugou('/song/url', params, user_id=user_id)
    tracker_url = payload.get('url')
    url = ''
    if isinstance(tracker_url, str):
        url = tracker_url
    elif isinstance(tracker_url, list):
        for item in tracker_url:
            if isinstance(item, str) and item:
                url = item
                break

    return {
        'url': url or '',
        'quality': str(payload.get('bitRate') or payload.get('quality') or quality),
        'expires_at': payload.get('expire'),
        'raw': payload,
    }


def get_track_lyric(
    user_id: int,
    title: str,
    artist: str,
    hash_value: str,
    album_audio_id: str | None,
    duration: int,
) -> dict[str, Any]:
    keyword = f'{artist} - {title}' if artist else title
    lyric_search = _request_kugou('/search/lyric', {
        'keywords': keyword,
        'hash': hash_value,
        'album_audio_id': album_audio_id or 0,
        'duration': duration,
        'man': 'no',
    }, user_id=user_id)
    candidates = lyric_search.get('candidates')
    if not isinstance(candidates, list) or not candidates:
        return {'lines': [], 'raw': ''}

    lyric_candidate = candidates[0]
    if not isinstance(lyric_candidate, dict):
        return {'lines': [], 'raw': ''}

    lyric_id = str(lyric_candidate.get('id') or '')
    access_key = str(lyric_candidate.get('accesskey') or '')
    if not lyric_id or not access_key:
        return {'lines': [], 'raw': ''}

    lyric_payload = _request_kugou('/lyric', {
        'id': lyric_id,
        'accesskey': access_key,
        'fmt': 'lrc',
        'decode': 'true',
    }, user_id=user_id)
    content = str(lyric_payload.get('decodeContent') or '')

    return {
        'lines': _parse_lrc(content),
        'raw': content,
    }


def get_auth_status(user_id: int) -> dict[str, Any]:
    cookie = _effective_cookie(user_id)
    return {
        'logged_in': bool(_cookie_value(cookie, 'token') and _cookie_value(cookie, 'userid')),
        'source': 'redis' if _get_user_cookie(user_id) else ('env' if settings.KUGOU_MUSIC_COOKIE else ''),
        'userid': _cookie_value(cookie, 'userid'),
    }


def create_qr_login() -> dict[str, Any]:
    key_payload = _request_kugou('/login/qr/key', {})
    key_data = key_payload.get('data') if isinstance(key_payload.get('data'), dict) else {}
    key = key_data.get('qrcode') or key_data.get('key') or key_data.get('qr_code') or key_data.get('qrcode_txt')
    if not key:
        raise MusicServiceError('KuGouMusicApi did not return QR login key')

    qr_payload = _request_kugou('/login/qr/create', {'key': key, 'qrimg': 1})
    qr_data = qr_payload.get('data') if isinstance(qr_payload.get('data'), dict) else {}
    return {
        'key': key,
        'url': qr_data.get('url') or '',
        'base64': qr_data.get('base64') or '',
    }


def check_qr_login(user_id: int, key: str) -> dict[str, Any]:
    payload = _request_kugou('/login/qr/check', {'key': key, 'timestamp': _timestamp_ms()})
    data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
    status = int(data.get('status') or 0)
    if status == 4:
        _save_user_cookie_from_login(user_id, data)

    return {
        'status': status,
        'logged_in': status == 4,
        'auth': get_auth_status(user_id),
        'raw': data,
    }


def _request_kugou(
    path: str,
    params: dict[str, Any],
    *,
    use_auth: bool = True,
    user_id: int | None = None,
) -> dict[str, Any]:
    if not settings.KUGOU_MUSIC_API_BASE_URL:
        raise MusicServiceError('KUGOU_MUSIC_API_BASE_URL is not configured')

    headers = {}
    cookie = _effective_cookie(user_id)
    if use_auth and cookie:
        headers['Authorization'] = cookie

    try:
        with httpx.Client(timeout=20.0, follow_redirects=True) as client:
            result = client.get(
                urljoin(settings.KUGOU_MUSIC_API_BASE_URL.rstrip('/') + '/', path.lstrip('/')),
                params=params,
                headers=headers,
            )
    except httpx.HTTPError as exc:
        raise MusicServiceError(f'KuGouMusicApi request failed: {exc}') from exc

    try:
        payload = result.json()
    except ValueError as exc:
        content_type = result.headers.get('content-type', '')
        body_preview = result.text[:200].replace('\n', ' ').replace('\r', ' ')
        raise MusicServiceError(
            f'KuGouMusicApi returned non-JSON response: status={result.status_code} '
            f'content_type={content_type} body={body_preview}'
        ) from exc

    if not isinstance(payload, dict):
        raise MusicServiceError('KuGouMusicApi returned invalid payload')

    error_code = payload.get('error_code')
    if error_code in (None, '', 0, '0', 200, '200'):
        error_code = payload.get('errcode')
    if error_code not in (None, '', 0, '0', 200, '200'):
        message = (
            payload.get('error')
            or payload.get('message')
            or payload.get('msg')
            or payload.get('error_msg')
            or payload.get('errmsg')
            or 'KuGouMusicApi rejected request'
        )
        raise MusicServiceError(str(message))

    try:
        result.raise_for_status()
    except httpx.HTTPError as exc:
        raise MusicServiceError(f'KuGouMusicApi request failed: {exc}') from exc

    return payload


def _save_user_cookie_from_login(user_id: int, data: dict[str, Any]) -> None:
    token = str(data.get('token') or '')
    kugou_userid = str(data.get('userid') or '')
    if not token or not kugou_userid:
        raise MusicServiceError('KuGouMusicApi login response missed token or userid')

    dfid = _cookie_value(_effective_cookie(user_id), 'dfid')
    if not dfid:
        register_payload = _request_kugou('/register/dev', {}, use_auth=False)
        register_data = register_payload.get('data') if isinstance(register_payload.get('data'), dict) else {}
        dfid = str(register_data.get('dfid') or '')

    if not dfid:
        raise MusicServiceError('KuGouMusicApi did not return dfid')

    redis_client.set(_auth_redis_key(user_id), f'token={token};userid={kugou_userid};dfid={dfid}')


def _effective_cookie(user_id: int | None = None) -> str:
    if user_id is not None:
        user_cookie = _get_user_cookie(user_id)
        if user_cookie:
            return user_cookie
    return settings.KUGOU_MUSIC_COOKIE


def _get_user_cookie(user_id: int) -> str:
    value = redis_client.get(_auth_redis_key(user_id))
    if isinstance(value, bytes):
        return value.decode('utf-8')
    return str(value or '')


def _auth_redis_key(user_id: int) -> str:
    return f'{KUGOU_AUTH_REDIS_KEY_PREFIX}:{user_id}'


def _cookie_value(cookie: str, key: str) -> str:
    prefix = f'{key}='
    for item in cookie.split(';'):
        normalized = item.strip()
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return ''


def _timestamp_ms() -> int:
    import time
    return int(time.time() * 1000)


def _parse_lrc(content: str) -> list[dict[str, Any]]:
    lines = []
    for raw_line in content.splitlines():
        if not raw_line.startswith('[') or ']' not in raw_line:
            continue
        text = raw_line[raw_line.rfind(']') + 1:].strip()
        for timestamp in raw_line[:raw_line.rfind(']') + 1].split(']'):
            if not timestamp.startswith('['):
                continue
            seconds = _parse_lrc_timestamp(timestamp[1:])
            if seconds >= 0:
                lines.append({'time': seconds, 'text': text})
    return sorted(lines, key=lambda item: item['time'])


def _parse_lrc_timestamp(value: str) -> float:
    if ':' not in value:
        return -1
    minutes_text, seconds_text = value.split(':', 1)
    try:
        return int(minutes_text) * 60 + float(seconds_text)
    except ValueError:
        return -1


def _normalize_rank(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('rankid') or row.get('id') or ''),
        'rank_cid': str(row.get('rank_cid') or ''),
        'name': row.get('rankname') or '',
        'cover': _format_image_url(row.get('imgurl') or row.get('album_img_9') or row.get('banner_9') or ''),
        'intro': row.get('intro') or '',
        'update_frequency': row.get('update_frequency') or '',
        'play_count': int(row.get('play_times') or 0),
    }


def _normalize_playlist(row: dict[str, Any]) -> dict[str, Any]:
    tags = row.get('tags')
    if not isinstance(tags, list):
        tags = []

    return {
        'id': str(row.get('global_collection_id') or ''),
        'name': row.get('specialname') or '',
        'cover': _format_image_url(row.get('flexible_cover') or row.get('imgurl') or ''),
        'intro': row.get('intro') or '',
        'creator': row.get('nickname') or '',
        'play_count': int(row.get('play_count') or 0),
        'collect_count': int(row.get('collectcount') or 0),
        'tags': [tag.get('tag_name') for tag in tags if isinstance(tag, dict) and tag.get('tag_name')],
        'list_create_userid': str(row.get('list_create_userid') or row.get('suid') or ''),
        'list_create_listid': str(row.get('list_create_listid') or row.get('specialid') or ''),
        'list_create_gid': str(row.get('list_create_gid') or row.get('global_collection_id') or ''),
    }


def _normalize_user_playlist(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('listid') or row.get('list_id') or row.get('id') or ''),
        'name': row.get('name') or row.get('listname') or row.get('specialname') or '',
        'cover': _format_image_url(row.get('pic') or row.get('cover') or row.get('imgurl') or ''),
        'song_count': int(row.get('count') or row.get('song_count') or row.get('filecount') or 0),
        'is_default': bool(row.get('is_default') or row.get('is_def')),
        'is_collected': bool(row.get('is_collected') or row.get('type') == 1),
        'list_create_userid': str(row.get('list_create_userid') or row.get('userid') or ''),
        'list_create_listid': str(row.get('list_create_listid') or row.get('listid') or ''),
        'list_create_gid': str(row.get('list_create_gid') or row.get('gid') or ''),
    }


def _normalize_artist(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('author_id') or ''),
        'name': row.get('author_name') or '',
        'avatar': _format_image_url(row.get('sizable_avatar') or ''),
        'intro': row.get('intro') or '',
        'song_count': int(row.get('song_count') or 0),
        'album_count': int(row.get('album_count') or 0),
        'fan_count': int(row.get('fansnums') or 0),
    }


def _normalize_artist_search(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('AuthorId') or row.get('author_id') or ''),
        'name': row.get('AuthorName') or row.get('author_name') or '',
        'avatar': _format_image_url(row.get('Avatar') or row.get('sizable_avatar') or ''),
        'intro': row.get('Auxiliary') or row.get('intro') or '',
        'song_count': int(row.get('AudioCount') or row.get('song_count') or 0),
        'album_count': int(row.get('AlbumCount') or row.get('album_count') or 0),
        'fan_count': int(row.get('FansNum') or row.get('fansnums') or 0),
    }


def _normalize_album(row: dict[str, Any]) -> dict[str, Any]:
    authors = row.get('authors') if isinstance(row.get('authors'), list) else []
    first_author = next((item for item in authors if isinstance(item, dict)), {})
    return {
        'id': str(row.get('album_id') or ''),
        'name': row.get('album_name') or '',
        'cover': _format_image_url(row.get('sizable_cover') or ''),
        'intro': row.get('intro') or '',
        'artist': row.get('author_name') or first_author.get('author_name') or '',
        'artist_id': str(first_author.get('author_id') or ''),
        'publish_date': row.get('publish_date') or '',
        'language': row.get('language') or '',
        'type': row.get('type') or '',
        'heat': int(row.get('heat') or 0),
    }


def _normalize_album_from_track(row: dict[str, Any]) -> dict[str, Any]:
    album_info = row.get('album_info') if isinstance(row.get('album_info'), dict) else {}
    album_id = str(row.get('AlbumID') or row.get('album_id') or '')
    album_name = row.get('AlbumName') or album_info.get('album_name') or row.get('album_name') or ''
    artist_id = _artist_id(row)
    return {
        'id': album_id,
        'name': album_name,
        'cover': _format_image_url(row.get('Image') or row.get('cover') or album_info.get('sizable_cover') or ''),
        'intro': '',
        'artist': row.get('SingerName') or row.get('author_name') or _artist_names(row),
        'artist_id': artist_id,
        'publish_date': '',
        'language': '',
        'type': '',
        'heat': 0,
    }


def _normalize_track(row: dict[str, Any]) -> dict[str, Any]:
    audio_info = row.get('audio_info') if isinstance(row.get('audio_info'), dict) else {}
    album_info = row.get('album_info') if isinstance(row.get('album_info'), dict) else {}
    albuminfo = row.get('albuminfo') if isinstance(row.get('albuminfo'), dict) else {}
    base = row.get('base') if isinstance(row.get('base'), dict) else {}
    trans_param = row.get('trans_param') if isinstance(row.get('trans_param'), dict) else {}
    artist = row.get('SingerName') or row.get('author_name') or base.get('author_name') or row.get('singername') or _artist_names(row)
    title = (
        row.get('SongName') or row.get('FileName') or row.get('songname') or base.get('audio_name')
        or row.get('audio_name') or row.get('name') or ''
    )
    if title and artist:
        title = str(title).strip()
        for suffix in ('.mp3', '.flac', '.m4a', '.aac', '.wav', '.ogg'):
            if title.lower().endswith(suffix):
                title = title[:-len(suffix)].strip()
                break
        for artist_name in [str(artist), *str(artist).split('、')]:
            prefix = f'{artist_name} - '
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
                break
    duration = (
        row.get('Duration')
        or row.get('time_length')
        or _milliseconds_to_seconds(row.get('timelen'))
        or _milliseconds_to_seconds(
            audio_info.get('duration_128') or audio_info.get('duration') or row.get('timelength_128')
        )
    )
    payload = {
        'id': str(
            row.get('AlbumAudioID')
            or row.get('MixSongID')
            or row.get('album_audio_id')
            or row.get('add_mixsongid')
            or row.get('mixsongid')
            or base.get('album_audio_id')
            or row.get('Audioid')
            or row.get('audio_id')
            or row.get('FileHash')
            or row.get('hash')
            or ''
        ),
        'title': title,
        'artist': artist,
        'album': row.get('AlbumName') or album_info.get('album_name') or albuminfo.get('name') or row.get('album_name') or row.get('remark') or '',
        'hash': row.get('FileHash') or row.get('hash') or audio_info.get('hash_128') or audio_info.get('hash') or '',
        'album_id': str(row.get('AlbumID') or row.get('album_id') or base.get('album_id') or albuminfo.get('id') or ''),
        'album_audio_id': str(
            row.get('AlbumAudioID') or row.get('MixSongID') or row.get('album_audio_id') or row.get('add_mixsongid')
            or row.get('mixsongid') or base.get('album_audio_id') or ''
        ),
        'duration': int(duration or 0),
        'cover': _format_image_url(
            row.get('Image') or row.get('cover') or album_info.get('sizable_cover') or album_info.get('cover')
            or row.get('sizable_cover') or trans_param.get('union_cover') or ''
        ),
    }
    artist_id = _artist_id(row)
    if artist_id:
        payload['artist_id'] = artist_id
    file_id = str(row.get('fileid') or row.get('file_id') or '')
    if file_id:
        payload['file_id'] = file_id
    return payload


def _artist_names(row: dict[str, Any]) -> str:
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


def _artist_id(row: dict[str, Any]) -> str:
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


def _milliseconds_to_seconds(value: Any) -> int:
    try:
        milliseconds = int(value or 0)
    except (TypeError, ValueError):
        return 0
    if milliseconds > 1000:
        return round(milliseconds / 1000)
    return milliseconds


def _format_image_url(value: str) -> str:
    return value.replace('{size}', '240') if value else ''


def _first_list(data: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _playlist_track_data(track: MusicTrackPayload) -> str:
    return '|'.join([track.title, track.hash, track.album_id, track.album_audio_id])
