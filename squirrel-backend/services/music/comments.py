"""Comments: song, classify, hotword, floor, playlist, album, count."""

import logging
from typing import Any

from services.music._client import _request_kugou
from services.music._normalizers import _first_list, _normalize_comment

logger = logging.getLogger(__name__)


async def get_song_comments(user_id: int, mixsong_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/comment/music", {
        "mixsongid": mixsong_id,
        "p": page,
        "pagesize": page_size,
    }, user_id=user_id)
    logger.debug("comment/music response keys=%s mixsongid=%s", list(payload.keys()), mixsong_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    if isinstance(data, dict):
        logger.debug("comment/music data keys=%s", list(data.keys()))
    rows = _first_list(data, ("cmtlist", "list", "lists", "comments", "info", "items", "data"))
    logger.debug("comment/music resolved rows count=%d", len(rows))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or data.get("cmtcount") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_comment(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_song_comments_classify(user_id: int, mixsong_id: str, type_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/comment/music/classify", {
        "mixsongid": mixsong_id,
        "type_id": type_id,
        "page": page,
        "pagesize": page_size,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("cmtlist", "list", "lists", "comments", "info", "items", "data"))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_comment(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_song_comments_hotword(user_id: int, mixsong_id: str) -> dict[str, Any]:
    payload = await _request_kugou("/comment/music/hotword", {
        "mixsongid": mixsong_id,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("cmtlist", "list", "lists", "comments", "info", "items", "data"))
    return {
        "items": [
            {
                "keyword": str(row.get("keyword") or row.get("word") or row.get("hotword") or ""),
                "count": int(row.get("count") or row.get("num") or 0),
            }
            for row in rows
        ],
    }


async def get_floor_comments(user_id: int, special_id: str, mixsong_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    params: dict[str, Any] = {
        "special_id": special_id,
        "p": page,
        "pagesize": page_size,
    }
    if mixsong_id:
        params["mixsongid"] = mixsong_id
    payload = await _request_kugou("/comment/floor", params, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("cmtlist", "list", "lists", "comments", "info", "items", "data"))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_comment(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_playlist_comments(user_id: int, playlist_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/comment/playlist", {
        "id": playlist_id,
        "p": page,
        "pagesize": page_size,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("cmtlist", "list", "lists", "comments", "info", "items", "data"))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_comment(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_album_comments(user_id: int, album_id: str, page: int, page_size: int) -> dict[str, Any]:
    payload = await _request_kugou("/comment/album", {
        "id": album_id,
        "p": page,
        "pagesize": page_size,
    }, user_id=user_id)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    rows = _first_list(data, ("cmtlist", "list", "lists", "comments", "info", "items", "data"))
    if isinstance(data, dict):
        total = data.get("total") or data.get("count") or len(rows)
    else:
        total = len(rows)

    return {
        "items": [_normalize_comment(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
    }


async def get_comment_counts(user_id: int, hash_value: str) -> dict[str, Any]:
    payload = await _request_kugou("/comment/count", {
        "hash": hash_value,
    }, user_id=user_id, use_auth=False)
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    count = 0
    if isinstance(data, dict):
        count = int(data.get("count") or data.get("cmtcount") or data.get("num") or 0)
    elif isinstance(data, (int, float)):
        count = int(data)
    return {
        "count": count,
    }
