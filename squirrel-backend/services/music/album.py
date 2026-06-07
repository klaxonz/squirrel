"""Album detail and tracks."""

from typing import Any

from services.music._client import _request_kugou
from services.music._normalizers import _normalize_album, _normalize_track


async def get_album_detail(user_id: int, album_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/album/detail", {"id": album_id}, user_id=user_id)
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    row = rows[0] if rows and isinstance(rows[0], dict) else {}
    return _normalize_album(row)


async def get_album_tracks(user_id: int, album_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/album/songs", {
        "id": album_id,
        "page": page,
        "pagesize": page_size,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    rows = data.get("songs") if isinstance(data.get("songs"), list) else []
    return {
        "items": [_normalize_track(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": data.get("total") or payload.get("total") or len(rows),
    }
