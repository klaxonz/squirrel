"""KuGouMusicApi HTTP client, cookie helpers, and the shared service error type."""

import logging
import time
from typing import Any
from urllib.parse import urljoin

import anyio
import httpx

from core.cache import redis_client
from core.config import settings

logger = logging.getLogger(__name__)


KUGOU_AUTH_REDIS_KEY_PREFIX = "music:kugou:auth"
_http_client: httpx.AsyncClient | None = None


class MusicServiceError(Exception):
    pass


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
    return _http_client


def _timestamp_ms() -> int:
    return int(time.time() * 1000)


async def _request_kugou(
    path: str,
    params: dict[str, Any],
    *,
    use_auth: bool = True,
    user_id: int | None = None,
) -> dict[str, Any]:
    if not settings.KUGOU_MUSIC_API_BASE_URL:
        raise MusicServiceError("KUGOU_MUSIC_API_BASE_URL is not configured")

    headers = {}
    if use_auth:
        cookie = await _effective_cookie(user_id)
        if cookie:
            headers["Authorization"] = cookie

    client = get_http_client()
    try:
        result = await client.get(
            urljoin(settings.KUGOU_MUSIC_API_BASE_URL.rstrip("/") + "/", path.lstrip("/")),
            params=params,
            headers=headers,
        )
    except httpx.HTTPError as exc:
        raise MusicServiceError(f"KuGouMusicApi request failed: {exc}") from exc

    try:
        result.raise_for_status()
    except httpx.HTTPError as exc:
        raise MusicServiceError(f"KuGouMusicApi request failed: {exc}") from exc

    try:
        payload = result.json()
    except ValueError as exc:
        content_type = result.headers.get("content-type", "")
        body_preview = result.text[:200].replace("\n", " ").replace("\r", " ")
        raise MusicServiceError(
            f"KuGouMusicApi returned non-JSON response: status={result.status_code} "
            f"content_type={content_type} body={body_preview}",
        ) from exc

    if not isinstance(payload, dict):
        raise MusicServiceError("KuGouMusicApi returned invalid payload")

    error_code = payload.get("error_code")
    if error_code in (None, "", 0, "0", 200, "200"):
        error_code = payload.get("errcode")
    if error_code not in (None, "", 0, "0", 200, "200"):
        message = (
            payload.get("error")
            or payload.get("message")
            or payload.get("msg")
            or payload.get("error_msg")
            or payload.get("errmsg")
            or "KuGouMusicApi rejected request"
        )
        raise MusicServiceError(str(message))

    return payload


async def _effective_cookie(user_id: int | None = None) -> str:
    if user_id is not None:
        user_cookie = await _get_user_cookie(user_id)
        if user_cookie:
            return user_cookie
    return settings.KUGOU_MUSIC_COOKIE


async def _get_user_cookie(user_id: int) -> str:
    value = await anyio.to_thread.run_sync(redis_client.get, _auth_redis_key(user_id))
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value or "")


def _auth_redis_key(user_id: int) -> str:
    return f"{KUGOU_AUTH_REDIS_KEY_PREFIX}:{user_id}"


def _cookie_value(cookie: str, key: str) -> str:
    prefix = f"{key}="
    for item in cookie.split(";"):
        normalized = item.strip()
        if normalized.startswith(prefix):
            return normalized[len(prefix):]
    return ""
