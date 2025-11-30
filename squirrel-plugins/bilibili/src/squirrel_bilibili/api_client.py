from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from http.cookies import SimpleCookie
from typing import Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from bilibili_api import Credential, ResourceType, parse_link, sync
from bilibili_api import video as bili_video

from crawl import (
    filter_cookies_to_query_string,
    get_rate_limiter,
)


@dataclass
class VideoContext:
    video: bili_video.Video
    credential: Credential
    page_index: int
    cid: Optional[int]


_rate_limiter = get_rate_limiter()


def throttled_sync(coro):
    """Use shared rate limiter to avoid hitting anti-spider limits."""
    _rate_limiter.wait("bilibili.com")
    return sync(coro)


def _load_cookies(cookie_string: str) -> Dict[str, str]:
    cookie_jar = SimpleCookie()
    if cookie_string:
        cookie_jar.load(cookie_string)
    return {k: morsel.value for k, morsel in cookie_jar.items()}


def _pick_cookie(cookies: Dict[str, str], name: str) -> Optional[str]:
    for key, value in cookies.items():
        if key.lower() == name.lower():
            return value
    return None


def build_credential(target_url: str) -> Credential:
    """Build a bilibili-api Credential from the configured cookie file."""
    cookie_string = filter_cookies_to_query_string(target_url)
    cookies = _load_cookies(cookie_string)
    return Credential(
        sessdata=_pick_cookie(cookies, "SESSDATA"),
        bili_jct=_pick_cookie(cookies, "bili_jct"),
        buvid3=_pick_cookie(cookies, "buvid3"),
        buvid4=_pick_cookie(cookies, "buvid4"),
        dedeuserid=_pick_cookie(cookies, "DedeUserID"),
        ac_time_value=_pick_cookie(cookies, "ac_time_value"),
    )


def extract_page_index(target_url: str) -> int:
    """Parse the page index (`p` query param) from a bilibili video URL."""
    query = parse_qs(urlparse(target_url).query)
    page_values = query.get("p") or query.get("page")
    if page_values:
        try:
            return max(int(page_values[0]) - 1, 0)
        except (TypeError, ValueError):
            pass
    return 0


def get_video_context(
    url: str, credential: Optional[Credential] = None
) -> VideoContext:
    """Resolve the Video object, credential and cid for the given URL."""
    credential = credential or build_credential(url)
    obj, resource_type = throttled_sync(parse_link(url, credential))
    if obj == -1 or resource_type != ResourceType.VIDEO:
        raise ValueError("URL is not a supported bilibili video link")

    video_obj: bili_video.Video = obj  # type: ignore[assignment]
    video_obj.credential = credential

    page_index = extract_page_index(url)
    cid: Optional[int] = None
    try:
        pages = throttled_sync(video_obj.get_pages())
        if pages:
            page_index = min(page_index, len(pages) - 1)
            cid = pages[page_index].get("cid")
    except Exception:
        # Fallback: rely on download_url to resolve cid later.
        pass

    return VideoContext(video_obj, credential, page_index, cid)


def fetch_video_info(
    url: str, credential: Optional[Credential] = None
) -> Tuple[dict, VideoContext, Optional[dict]]:
    """Fetch base video info along with context and selected page."""
    context = get_video_context(url, credential)
    info = throttled_sync(context.video.get_info())

    pages = info.get("pages") or []
    page_info: Optional[dict] = None
    if pages:
        index = min(context.page_index, len(pages) - 1)
        page_info = pages[index]
        if context.cid is None:
            context.cid = page_info.get("cid")

    return info, context, page_info


def build_base_info(
    info: dict, context: VideoContext, page_info: Optional[dict]
) -> dict:
    """Normalise bilibili-api video info into the base_info shape expected by the SDK."""
    publish_timestamp = info.get("pubdate")
    publish_date = (
        datetime.fromtimestamp(publish_timestamp) if publish_timestamp else None
    )
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
    url: str, context: Optional[VideoContext] = None
) -> Tuple[dict, VideoContext]:
    """Fetch playurl (dash) info for the given video URL."""
    context = context or get_video_context(url)
    params = {}
    if context.cid is not None:
        params["cid"] = context.cid
    else:
        params["page_index"] = context.page_index

    play_data = throttled_sync(context.video.get_download_url(**params))
    if isinstance(play_data, dict) and play_data.get("video_info"):
        play_data = play_data["video_info"]

    return play_data, context
