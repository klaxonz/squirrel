"""Artist detail, tracks/albums, follow, directory, videos, honours."""

from typing import Any

from services.music._client import _request_kugou
from services.music._normalizers import (
    _first_list,
    _normalize_album,
    _normalize_artist,
    _normalize_track,
    _normalize_video,
)


async def get_artist_detail(user_id: int, artist_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/artist/detail", {"id": artist_id}, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return _normalize_artist(data)


async def get_artist_tracks(user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/artist/audios", {
        "id": artist_id,
        "page": page,
        "pagesize": page_size,
    }, user_id=user_id)
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    return {
        "items": [_normalize_track(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": payload.get("total") or len(rows),
    }


async def get_artist_albums(user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/artist/albums", {
        "id": artist_id,
        "page": page,
        "pagesize": page_size,
    }, user_id=user_id)
    rows = payload.get("data") if isinstance(payload.get("data"), list) else []
    return {
        "items": [_normalize_album(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": payload.get("total") or len(rows),
    }


async def follow_artist(user_id: int, artist_id: str) -> dict[str, Any]:
    await _request_kugou("/artist/follow", {
        "id": artist_id,
    }, user_id=user_id)
    return {"ok": True}


async def unfollow_artist(user_id: int, artist_id: str) -> dict[str, Any]:
    await _request_kugou("/artist/unfollow", {
        "id": artist_id,
    }, user_id=user_id)
    return {"ok": True}


async def get_followed_artists_new_songs(user_id: int) -> dict[str, Any]:
    payload = await _request_kugou("/artist/follow/newsongs", {}, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("songs", "info", "list", "data"))
    return {
        "items": [_normalize_track(row) for row in rows],
    }


async def get_user_followed_artists(user_id: int) -> dict[str, Any]:
    payload = await _request_kugou("/user/follow", {}, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("info", "list", "lists", "data"))
    return {
        "items": [_normalize_artist(row) for row in rows],
    }


async def list_artist_directory(user_id: int, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/artist/lists", {
        "page": page,
        "pagesize": page_size,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("info", "list", "lists", "data"))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_artist(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_artist_videos(user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/artist/videos", {
        "id": artist_id,
        "page": page,
        "pagesize": page_size,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("info", "list", "lists", "videos", "data"))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_video(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_artist_honour(user_id: int, artist_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/artist/honour", {
        "id": artist_id,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("info", "list", "lists", "honours", "data"))
    return {
        "items": [
            {
                "title": str(row.get("title") or row.get("name") or ""),
                "description": str(row.get("desc") or row.get("description") or ""),
                "date": str(row.get("date") or row.get("time") or ""),
            }
            for row in rows
        ],
    }
