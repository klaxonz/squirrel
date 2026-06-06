from __future__ import annotations

import re
import time
import urllib.parse
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import reduce
from hashlib import md5
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urljoin, urlparse

from crawl import filter_cookies_to_query_string, get_http_headers, request, request_without_limit

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

_WBI_KEY_CACHE: tuple[str, str] | None = None
_WBI_KEY_CACHE_TS: float | None = None
_WBI_KEY_CACHE_TTL_SECONDS = 3600

_DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com/',
    'Accept': 'application/json',
}

_BV_RE = re.compile(r'(BV[0-9A-Za-z]{10,})')
_AV_RE = re.compile(r'/av(\d+)', re.IGNORECASE)

_BILIBILI_DOMAIN = 'bilibili.com'


def get_mixin_key(orig: str) -> str:
    return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, '')[:32]


def enc_wbi(params: Dict[str, str], img_key: str, sub_key: str) -> Dict[str, str]:
    mixin_key = get_mixin_key(img_key + sub_key)
    curr_time = round(time.time())
    params = dict(params)
    params['wts'] = str(curr_time)
    params = dict(sorted(params.items()))
    params = {k: ''.join(ch for ch in str(v) if ch not in "!'()*") for k, v in params.items()}
    query = urllib.parse.urlencode(params)
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()
    params['w_rid'] = wbi_sign
    return params


def get_wbi_keys() -> tuple[str, str]:
    global _WBI_KEY_CACHE, _WBI_KEY_CACHE_TS
    if _WBI_KEY_CACHE and _WBI_KEY_CACHE_TS is not None:
        if (time.time() - _WBI_KEY_CACHE_TS) < _WBI_KEY_CACHE_TTL_SECONDS:
            return _WBI_KEY_CACHE

    headers = get_http_headers(SITE_SLUG, {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': 'https://www.bilibili.com/'
    })
    resp = request(
        'GET',
        'https://api.bilibili.com/x/web-interface/nav',
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()
    json_content = resp.json()
    img_url: str = json_content['data']['wbi_img']['img_url']
    sub_url: str = json_content['data']['wbi_img']['sub_url']
    img_key = img_url.rsplit('/', 1)[1].split('.')[0]
    sub_key = sub_url.rsplit('/', 1)[1].split('.')[0]
    _WBI_KEY_CACHE = (img_key, sub_key)
    _WBI_KEY_CACHE_TS = time.time()
    return img_key, sub_key


def sign(params: Dict[str, str]) -> str:
    img_key, sub_key = get_wbi_keys()
    signed_params = enc_wbi(params, img_key, sub_key)
    return urllib.parse.urlencode(signed_params)


def sign_params(params: Dict[str, str]) -> Dict[str, str]:
    img_key, sub_key = get_wbi_keys()
    return enc_wbi(params, img_key, sub_key)


SITE_SLUG = 'bilibili'


@dataclass
class VideoContext:
    bvid: Optional[str]
    aid: Optional[int]
    url: str
    cookies: str
    page_index: int
    cid: Optional[int]


class ResourceType(str, Enum):
    VIDEO = 'video'
    USER = 'user'
    FAVORITE_LIST = 'favorite_list'
    CHANNEL_SERIES = 'channel_series'


class ChannelSeriesType(str, Enum):
    SERIES = 'series'
    SEASON = 'season'


@dataclass(frozen=True)
class ParsedSubscriptionTarget:
    resource_type: ResourceType
    mid: Optional[int] = None
    media_id: Optional[int] = None
    series_id: Optional[int] = None
    series_type: Optional[ChannelSeriesType] = None


def _cookie_source_url(target_url: str) -> str:
    parsed = urlparse(target_url)
    host = (parsed.hostname or '').lower()
    if host.endswith('b23.tv'):
        return 'https://www.bilibili.com/'
    return target_url


def build_cookies(target_url: str) -> str:
    return filter_cookies_to_query_string(_cookie_source_url(target_url))


def _build_headers(cookies: str) -> Dict[str, str]:
    headers = get_http_headers(SITE_SLUG, _DEFAULT_HEADERS)
    if cookies:
        headers['Cookie'] = cookies
    return headers


def _send_request(
    method: str,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    cookies: str = '',
    timeout: float = 20,
    throttled: bool = True,
    allow_redirects: bool = True,
):
    kwargs: Dict[str, Any] = {
        'headers': _build_headers(cookies),
        'timeout': timeout,
        'allow_redirects': allow_redirects,
    }
    if params:
        kwargs['params'] = params
    if throttled:
        return request(method, url, **kwargs)
    return request_without_limit(method, url, **kwargs)


def _get_json(
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    cookies: str = '',
    throttled: bool = True,
    timeout: float = 20,
) -> dict:
    resp = _send_request(
        'GET',
        url,
        params=params,
        cookies=cookies,
        timeout=timeout,
        throttled=throttled,
        allow_redirects=True,
    )
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, dict) and payload.get('code') not in (None, 0):
        code = payload.get('code')
        message = payload.get('message') or payload.get('msg') or str(code)
        raise RuntimeError(f'{message} (code={code})')
    if isinstance(payload, dict) and 'data' in payload:
        return payload.get('data') or {}
    return payload if isinstance(payload, dict) else {}


def _resolve_redirect_url(
    url: str,
    *,
    cookies: str = '',
    throttled: bool = True,
    max_hops: int = 5,
) -> str:
    current = url
    for _ in range(max_hops):
        resp = _send_request(
            'GET',
            current,
            cookies=cookies,
            timeout=15,
            throttled=throttled,
            allow_redirects=False,
        )
        if resp.is_redirect or resp.is_permanent_redirect or (300 <= resp.status_code < 400):
            location = resp.headers.get('Location') or resp.headers.get('location')
            if not location:
                break
            current = urljoin(current, location)
            continue
        break
    return current


def extract_page_index(target_url: str) -> int:
    query = parse_qs(urlparse(target_url).query)
    page_values = query.get('p') or query.get('page')
    if page_values:
        try:
            return max(int(page_values[0]) - 1, 0)
        except (TypeError, ValueError):
            pass
    return 0


def _parse_video_id(url: str) -> Tuple[Optional[str], Optional[int]]:
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
    bvid = (query.get('bvid') or [None])[0]
    if bvid and isinstance(bvid, str) and _BV_RE.match(bvid):
        return bvid, None
    aid = (query.get('aid') or query.get('avid') or [None])[0]
    if aid:
        try:
            return None, int(aid)
        except (ValueError, TypeError):
            pass
    return None, None


def normalize_video_url(url: str, *, cookies: str, throttled: bool = True) -> str:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if host.endswith('b23.tv'):
        return _resolve_redirect_url(url, cookies=cookies, throttled=throttled)
    return url


def fetch_video_info(
    url: str,
    cookies: Optional[str] = None,
    throttled: bool = True,
) -> Tuple[dict, VideoContext, Optional[dict]]:
    cookies = cookies if cookies is not None else build_cookies(url)
    resolved_url = normalize_video_url(url, cookies=cookies, throttled=throttled)
    page_index = extract_page_index(resolved_url)
    bvid, aid = _parse_video_id(resolved_url)
    if not bvid and not aid:
        raise ValueError('URL is not a supported bilibili video link')

    info = _get_json(
        'https://api.bilibili.com/x/web-interface/view',
        params={k: v for k, v in (('bvid', bvid), ('aid', aid)) if v is not None},
        cookies=cookies,
        throttled=throttled,
    )
    bvid = info.get('bvid') or bvid
    try:
        aid = int(info.get('aid')) if info.get('aid') is not None else aid
    except (ValueError, TypeError):
        aid = aid

    pages = info.get('pages') or []
    page_info: Optional[dict] = None
    cid: Optional[int] = None
    if pages and isinstance(pages, list):
        page_index = min(page_index, len(pages) - 1)
        page_info = pages[page_index]
        if page_info:
            try:
                cid = int(page_info.get('cid')) if page_info.get('cid') is not None else None
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
    cookies: Optional[str] = None,
    throttled: bool = True,
) -> VideoContext:
    _, context, _ = fetch_video_info(url, cookies=cookies, throttled=throttled)
    return context


def build_base_info(info: dict, context: VideoContext, page_info: Optional[dict]) -> dict:
    publish_timestamp = info.get('pubdate')
    publish_date = datetime.fromtimestamp(publish_timestamp) if publish_timestamp else None
    upload_date = publish_date.strftime('%Y%m%d') if publish_date else None

    duration = info.get('duration')
    if duration is None and page_info:
        duration = page_info.get('duration')

    return {
        'id': info.get('bvid') or info.get('aid'),
        'bvid': info.get('bvid'),
        'aid': info.get('aid'),
        'cid': context.cid,
        'title': info.get('title'),
        'description': info.get('desc'),
        'thumbnail': info.get('pic'),
        'duration': duration,
        'publish_date': publish_date,
        'upload_date': upload_date,
        'owner': info.get('owner'),
        'pages': info.get('pages'),
        'dynamic': info.get('dynamic'),
    }


def fetch_play_data(
    url: str,
    context: Optional[VideoContext] = None,
    throttled: bool = True,
) -> Tuple[dict, VideoContext]:
    context = context or get_video_context(url, throttled=throttled)
    if context.cid is None:
        raise RuntimeError('Failed to resolve cid')

    params: Dict[str, str] = {
        'cid': str(context.cid),
        'qn': '80',
        'fnver': '0',
        'fnval': '4048',
        'fourk': '1',
    }
    if context.bvid:
        params['bvid'] = context.bvid
    elif context.aid:
        params['aid'] = str(context.aid)
    else:
        raise RuntimeError('Missing video id')

    signed = sign_params(params)
    play_data = _get_json(
        'https://api.bilibili.com/x/player/wbi/playurl',
        params=signed,
        cookies=context.cookies,
        throttled=throttled,
        timeout=25,
    )
    return play_data, context


def parse_subscription_target(url: str) -> ParsedSubscriptionTarget:
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    query = parse_qs(parsed.query)
    path = parsed.path or ''

    if any(x in path for x in ('/favlist', '/fav/')) or 'fid' in query or 'media_id' in query or '/detail/ml' in path:
        media_id = (query.get('fid') or query.get('media_id') or [None])[0]
        if not media_id and '/detail/ml' in path:
            match = re.search(r'/detail/ml(\d+)', path, re.IGNORECASE)
            media_id = match.group(1) if match else None
        if not media_id:
            raise ValueError('Missing favorite list id')
        return ParsedSubscriptionTarget(resource_type=ResourceType.FAVORITE_LIST, media_id=int(media_id))

    if 'business' in query and ('series_id' in query or 'season_id' in query):
        business = (query.get('business') or [''])[0]
        mid = None
        if '/medialist/play/' in path:
            seg = [s for s in path.split('/') if s]
            if seg:
                try:
                    mid = int(seg[-1])
                except (ValueError, TypeError, IndexError):
                    mid = None
        series_type = ChannelSeriesType.SEASON if business == 'space_season' else ChannelSeriesType.SERIES
        id_value = (query.get('season_id') or query.get('series_id') or [None])[0]
        if not id_value:
            raise ValueError('Missing channel series id')
        return ParsedSubscriptionTarget(
            resource_type=ResourceType.CHANNEL_SERIES,
            mid=mid,
            series_id=int(id_value),
            series_type=series_type,
        )

    if '/channel/seriesdetail' in path or '/channel/collectiondetail' in path:
        seg = [s for s in path.split('/') if s]
        mid = None
        if host.endswith('space.bilibili.com') and seg:
            try:
                mid = int(seg[0])
            except (ValueError, TypeError, IndexError):
                mid = None
        sid = (query.get('sid') or query.get('series_id') or query.get('season_id') or [None])[0]
        if not sid:
            raise ValueError('Missing channel series id')
        series_type = ChannelSeriesType.SEASON if '/collectiondetail' in path or 'season' in path else ChannelSeriesType.SERIES
        return ParsedSubscriptionTarget(
            resource_type=ResourceType.CHANNEL_SERIES,
            mid=mid,
            series_id=int(sid),
            series_type=series_type,
        )

    if host.endswith('space.bilibili.com'):
        seg = [s for s in path.split('/') if s]
        if not seg:
            raise ValueError('Missing user id')
        return ParsedSubscriptionTarget(resource_type=ResourceType.USER, mid=int(seg[0]))

    mid = (query.get('mid') or query.get('vmid') or [None])[0]
    if mid:
        return ParsedSubscriptionTarget(resource_type=ResourceType.USER, mid=int(mid))

    raise ValueError('Unsupported bilibili subscription url')


def fetch_user_card(mid: int, *, cookies: str, throttled: bool = True) -> dict:
    return _get_json(
        'https://api.bilibili.com/x/web-interface/card',
        params={'mid': str(mid)},
        cookies=cookies,
        throttled=throttled,
    )


def fetch_user_videos(
    mid: int,
    *,
    cookies: str,
    pn: int,
    ps: int,
    throttled: bool = True,
) -> dict:
    params = sign_params(
        {
            'mid': str(mid),
            'pn': str(pn),
            'ps': str(ps),
            'order': 'pubdate',
        }
    )
    return _get_json(
        'https://api.bilibili.com/x/space/wbi/arc/search',
        params=params,
        cookies=cookies,
        throttled=throttled,
        timeout=25,
    )


def fetch_nav(*, cookies: str, throttled: bool = False) -> dict:
    return _get_json(
        'https://api.bilibili.com/x/web-interface/nav',
        params=None,
        cookies=cookies,
        throttled=throttled,
        timeout=15,
    )


def fetch_followings(
    mid: int,
    *,
    cookies: str,
    pn: int,
    ps: int,
    throttled: bool = False,
) -> dict:
    return _get_json(
        'https://api.bilibili.com/x/relation/followings',
        params={'vmid': str(mid), 'pn': str(pn), 'ps': str(ps), 'order': 'desc', 'order_type': 'attention'},
        cookies=cookies,
        throttled=throttled,
        timeout=20,
    )


def fetch_fav_folder_info(media_id: int, *, cookies: str, throttled: bool = True) -> dict:
    return _get_json(
        'https://api.bilibili.com/x/v3/fav/folder/info',
        params={'media_id': str(media_id)},
        cookies=cookies,
        throttled=throttled,
    )


def fetch_fav_resource_list(
    media_id: int,
    *,
    cookies: str,
    pn: int,
    ps: int = 20,
    throttled: bool = True,
) -> dict:
    return _get_json(
        'https://api.bilibili.com/x/v3/fav/resource/list',
        params={
            'media_id': str(media_id),
            'pn': str(pn),
            'ps': str(ps),
            'order': 'mtime',
            'type': '2',
        },
        cookies=cookies,
        throttled=throttled,
        timeout=25,
    )


def fetch_series_meta(
    *,
    mid: Optional[int],
    series_id: int,
    series_type: ChannelSeriesType,
    cookies: str,
    throttled: bool = True,
) -> dict:
    if series_type == ChannelSeriesType.SERIES:
        if not mid:
            return {}
        return _get_json(
            'https://api.bilibili.com/x/series/series',
            params={'mid': str(mid), 'series_id': str(series_id)},
            cookies=cookies,
            throttled=throttled,
            timeout=20,
        )

    if not mid:
        return {}
    data = _get_json(
        'https://api.bilibili.com/x/polymer/web-space/seasons_series_list',
        params={'mid': str(mid), 'page_num': '1', 'page_size': '50'},
        cookies=cookies,
        throttled=throttled,
        timeout=20,
    )
    items = data.get('items_list') or data.get('items_lists') or data.get('items') or []
    if isinstance(items, list):
        for item in items:
            try:
                if int(item.get('season_id') or item.get('id') or 0) == series_id:
                    return item
            except (ValueError, TypeError):
                continue
    return {}


def fetch_series_videos(
    *,
    mid: Optional[int],
    series_id: int,
    series_type: ChannelSeriesType,
    cookies: str,
    pn: int,
    ps: int,
    throttled: bool = True,
) -> dict:
    if not mid:
        raise ValueError('Missing mid for channel series url')

    if series_type == ChannelSeriesType.SERIES:
        return _get_json(
            'https://api.bilibili.com/x/series/archives',
            params={
                'mid': str(mid),
                'series_id': str(series_id),
                'only_normal': 'true',
                'sort': 'desc',
                'pn': str(pn),
                'ps': str(ps),
            },
            cookies=cookies,
            throttled=throttled,
            timeout=25,
        )

    return _get_json(
        'https://api.bilibili.com/x/polymer/web-space/seasons_archives_list',
        params={
            'mid': str(mid),
            'season_id': str(series_id),
            'page_num': str(pn),
            'page_size': str(ps),
        },
        cookies=cookies,
        throttled=throttled,
        timeout=25,
    )
