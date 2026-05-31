from typing import Any
from urllib.parse import urljoin

import httpx

from core.cache import redis_client
from core.config import settings


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


def get_track_play_url(user_id: int, hash_value: str, album_audio_id: str | None, quality: str) -> dict[str, Any]:
    params = {
        'hash': hash_value,
    }
    if album_audio_id:
        params['album_audio_id'] = album_audio_id

    payload = _request_kugou('/song/url/new', params, user_id=user_id)
    rows = payload.get('data') if isinstance(payload.get('data'), list) else []
    data = rows[0] if rows and isinstance(rows[0], dict) else {}
    info = data.get('info') if isinstance(data.get('info'), dict) else {}
    tracker_url = info.get('tracker_url')
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
        'quality': str(data.get('quality') or info.get('bitrate') or quality),
        'expires_at': data.get('expire'),
        'raw': data,
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
    if error_code:
        message = (
            payload.get('error')
            or payload.get('message')
            or payload.get('msg')
            or payload.get('error_msg')
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


def _normalize_track(row: dict[str, Any]) -> dict[str, Any]:
    title = row.get('SongName') or row.get('FileName') or ''
    artist = row.get('SingerName') or ''
    return {
        'id': str(row.get('AlbumAudioID') or row.get('MixSongID') or row.get('Audioid') or row.get('FileHash') or ''),
        'title': title,
        'artist': artist,
        'album': row.get('AlbumName') or '',
        'hash': row.get('FileHash') or '',
        'album_id': str(row.get('AlbumID') or ''),
        'album_audio_id': str(row.get('AlbumAudioID') or row.get('MixSongID') or ''),
        'duration': int(row.get('Duration') or 0),
        'cover': row.get('Image') or '',
    }
