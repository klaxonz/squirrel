from __future__ import annotations

import re
from enum import Enum
from urllib.parse import parse_qs, urlparse

from .api_client import _get_json
from .sign import sign_params


class ResourceType(str, Enum):
    VIDEO = 'video'
    USER = 'user'
    FAVORITE_LIST = 'favorite_list'
    CHANNEL_SERIES = 'channel_series'


class ChannelSeriesType(str, Enum):
    SERIES = 'series'
    SEASON = 'season'


class ParsedSubscriptionTarget:
    resource_type: ResourceType
    mid: int | None = None
    media_id: int | None = None
    series_id: int | None = None
    series_type: ChannelSeriesType | None = None

    def __init__(
        self,
        resource_type: ResourceType,
        mid: int | None = None,
        media_id: int | None = None,
        series_id: int | None = None,
        series_type: ChannelSeriesType | None = None,
    ):
        self.resource_type = resource_type
        self.mid = mid
        self.media_id = media_id
        self.series_id = series_id
        self.series_type = series_type


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
    mid: int | None,
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
    mid: int | None,
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
