"""Video: generic video detail/url/privilege (non-track-specific)."""

from typing import Any

from services.music._client import _request_kugou
from services.music._normalizers import _normalize_video


async def get_video_detail(user_id: int, video_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/video/detail", {
        "id": video_id,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return _normalize_video(data)


async def get_video_url(user_id: int, video_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/video/url", {
        "id": video_id,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    url = ""
    if isinstance(data, dict):
        url = str(data.get("url") or data.get("play_url") or data.get("video_url") or "")
    return {
        "url": url,
    }


async def get_video_privilege(user_id: int, video_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/video/privilege", {
        "id": video_id,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return {
        "id": str(data.get("id") or data.get("video_id") or ""),
        "playable": bool(data.get("playable") or data.get("can_play")),
        "downloadable": bool(data.get("downloadable") or data.get("can_download")),
        "quality": str(data.get("quality") or data.get("bitrate") or ""),
    }
