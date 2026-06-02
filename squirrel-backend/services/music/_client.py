"""KuGouMusicApi HTTP client, cookie helpers, and the shared service error type.

Runtime dependencies (``settings``, ``redis_client``, ``httpx``) are read
lazily from :mod:`services.music_service` so the test shim can swap them
via ``monkeypatch.setattr(music_service, 'redis_client', fake)``.
"""

import logging
from typing import Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


KUGOU_AUTH_REDIS_KEY_PREFIX = 'music:kugou:auth'


class MusicServiceError(Exception):
    pass


async def _request_kugou(
    path: str,
    params: dict[str, Any],
    *,
    use_auth: bool = True,
    user_id: int | None = None,
) -> dict[str, Any]:
    from services import music_service

    settings = music_service.settings
    if not settings.KUGOU_MUSIC_API_BASE_URL:
        raise MusicServiceError('KUGOU_MUSIC_API_BASE_URL is not configured')

    headers = {}
    if use_auth:
        cookie = await _effective_cookie(user_id)
        if cookie:
            headers['Authorization'] = cookie

    client = music_service.get_http_client()
    try:
        result = await client.get(
            urljoin(settings.KUGOU_MUSIC_API_BASE_URL.rstrip('/') + '/', path.lstrip('/')),
            params=params,
            headers=headers,
        )
    except music_service.httpx.HTTPError as exc:
        raise MusicServiceError(f'KuGouMusicApi request failed: {exc}') from exc

    try:
        result.raise_for_status()
    except music_service.httpx.HTTPError as exc:
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

    return payload


async def _effective_cookie(user_id: int | None = None) -> str:
    from services import music_service
    if user_id is not None:
        user_cookie = await _get_user_cookie(user_id)
        if user_cookie:
            return user_cookie
    return music_service.settings.KUGOU_MUSIC_COOKIE


async def _get_user_cookie(user_id: int) -> str:
    from services import music_service
    value = music_service.redis_client.get(_auth_redis_key(user_id))
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
