from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import parse_qs, urlparse

from .api_client import _get_json, _resolve_redirect_url, build_cookies

_BV_RE = re.compile(r"(BV[0-9A-Za-z]{10,})")
_AV_RE = re.compile(r"/av(\d+)", re.IGNORECASE)
_BILIBILI_DOMAIN = "bilibili.com"


@dataclass
class VideoContext:
    bvid: str | None
    aid: int | None
    url: str
    cookies: str
    page_index: int
    cid: int | None


def extract_page_index(target_url: str) -> int:
    query = parse_qs(urlparse(target_url).query)
    page_values = query.get("p") or query.get("page")
    if page_values:
        try:
            return max(int(page_values[0]) - 1, 0)
        except (TypeError, ValueError):
            pass
    return 0


def _parse_video_id(url: str) -> tuple[str | None, int | None]:
    match = _BV_RE.search(url)
    if match:
        return match.group(1), None
    match = _AV_RE.search(url)
    if match:
        try:
            return None, int(match.group(1))
        except (ValueError, TypeError):
            return None, None
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    bvid = (query.get("bvid") or [None])[0]
    if bvid and isinstance(bvid, str) and _BV_RE.match(bvid):
        return bvid, None
    aid = (query.get("aid") or query.get("avid") or [None])[0]
    if aid:
        try:
            return None, int(aid)
        except (ValueError, TypeError):
            pass
    return None, None


def normalize_video_url(url: str, *, cookies: str, throttled: bool = True) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if host.endswith("b23.tv"):
        return _resolve_redirect_url(url, cookies=cookies, throttled=throttled)
    return url


def fetch_video_info(
    url: str,
    cookies: str | None = None,
    throttled: bool = True,
) -> tuple[dict, VideoContext, dict | None]:
    cookies = cookies if cookies is not None else build_cookies(url)
    resolved_url = normalize_video_url(url, cookies=cookies, throttled=throttled)
    page_index = extract_page_index(resolved_url)
    bvid, aid = _parse_video_id(resolved_url)
    if not bvid and not aid:
        raise ValueError("URL is not a supported bilibili video link")

    info = _get_json(
        "https://api.bilibili.com/x/web-interface/view",
        params={k: v for k, v in (("bvid", bvid), ("aid", aid)) if v is not None},
        cookies=cookies,
        throttled=throttled,
    )
    bvid = info.get("bvid") or bvid
    try:
        aid = int(info.get("aid")) if info.get("aid") is not None else aid
    except (ValueError, TypeError):
        aid = aid

    pages = info.get("pages") or []
    page_info: dict | None = None
    cid: int | None = None
    if pages and isinstance(pages, list):
        page_index = min(page_index, len(pages) - 1)
        page_info = pages[page_index]
        if page_info:
            try:
                cid = int(page_info.get("cid")) if page_info.get("cid") is not None else None
            except (ValueError, TypeError):
                cid = None

    context = VideoContext(
        bvid=bvid,
        aid=aid,
        url=resolved_url,
        cookies=cookies,
        page_index=page_index,
        cid=cid,
    )
    return info, context, page_info


def get_video_context(
    url: str,
    cookies: str | None = None,
    throttled: bool = True,
) -> VideoContext:
    _, context, _ = fetch_video_info(url, cookies=cookies, throttled=throttled)
    return context


def build_base_info(info: dict, context: VideoContext, page_info: dict | None) -> dict:
    publish_timestamp = info.get("pubdate")
    publish_date = datetime.fromtimestamp(publish_timestamp) if publish_timestamp else None
    upload_date = publish_date.strftime("%Y%m%d") if publish_date else None

    duration = info.get("duration")
    if duration is None and page_info:
        duration = page_info.get("duration")

    return {
        "id": info.get("bvid") or info.get("aid"),
        "bvid": info.get("bvid"),
        "aid": info.get("aid"),
        "cid": context.cid,
        "title": info.get("title"),
        "description": info.get("desc"),
        "thumbnail": info.get("pic"),
        "duration": duration,
        "publish_date": publish_date,
        "upload_date": upload_date,
        "owner": info.get("owner"),
        "pages": info.get("pages"),
        "dynamic": info.get("dynamic"),
    }


def fetch_play_data(
    url: str,
    context: VideoContext | None = None,
    throttled: bool = True,
) -> tuple[dict, VideoContext]:
    ctx = context or get_video_context(url, throttled=throttled)
    if ctx.cid is None:
        raise RuntimeError("Failed to resolve cid")

    from .sign import sign_params

    params: dict[str, str] = {
        "cid": str(ctx.cid),
        "qn": "80",
        "fnver": "0",
        "fnval": "4048",
        "fourk": "1",
    }
    if ctx.bvid:
        params["bvid"] = ctx.bvid
    elif ctx.aid:
        params["aid"] = str(ctx.aid)
    else:
        raise RuntimeError("Missing video id")

    signed = sign_params(params)
    play_data = _get_json(
        "https://api.bilibili.com/x/player/wbi/playurl",
        params=signed,
        cookies=ctx.cookies,
        throttled=throttled,
        timeout=25,
    )
    return play_data, ctx
