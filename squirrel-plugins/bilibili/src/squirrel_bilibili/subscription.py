from __future__ import annotations

import logging
from typing import List, Optional

from crawl import (
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    append_subscription_video_url,
    build_subscription_sync_result,
    resolve_subscription_limit,
)

from .sign import (
    build_cookies,
    parse_subscription_target,
    ResourceType,
    ChannelSeriesType,
    fetch_fav_folder_info,
    fetch_fav_resource_list,
    fetch_series_meta,
    fetch_series_videos,
    fetch_user_card,
    fetch_user_videos,
)

logger = logging.getLogger(__name__)


class BilibiliSubscription:
    def __init__(self, url: str) -> None:
        self.url = url
        self.cookies = build_cookies(url)
        self.target = parse_subscription_target(url)
        self.resource_type = self.target.resource_type

    def get_subscribe_info(self) -> SubscriptionMeta:
        if self.resource_type == ResourceType.FAVORITE_LIST:
            return self._get_favlist_info()
        if self.resource_type == ResourceType.CHANNEL_SERIES:
            return self._get_channel_info()
        return self._get_space_info()

    def _get_space_info(self) -> SubscriptionMeta:
        if not self.target.mid:
            raise ValueError('Missing user id')
        info = fetch_user_card(self.target.mid, cookies=self.cookies, throttled=True)
        card = info.get('card') or info
        mid = card.get('mid') or self.target.mid
        channel_name = card.get('name') or card.get('uname')
        avatar_url = card.get('face')
        return SubscriptionMeta(str(mid), channel_name, avatar_url, self.url)

    def _get_favlist_info(self) -> SubscriptionMeta:
        if not self.target.media_id:
            raise ValueError('Missing favorite list id')
        info = fetch_fav_folder_info(self.target.media_id, cookies=self.cookies, throttled=True)
        data = info.get('info') or info
        title = data.get('title') or data.get('name') or 'Favorite List'
        cover = data.get('cover') or data.get('cover_url')
        return SubscriptionMeta(f"fav_{self.target.media_id}", title, cover, self.url)

    def _get_channel_info(self) -> SubscriptionMeta:
        if not self.target.series_id:
            raise ValueError('Missing channel series id')
        series_type = self.target.series_type or ChannelSeriesType.SERIES
        meta = fetch_series_meta(
            mid=self.target.mid,
            series_id=self.target.series_id,
            series_type=series_type,
            cookies=self.cookies,
            throttled=True,
        )
        data = meta.get('meta') or meta.get('data') or meta
        prefix = 'season' if series_type == ChannelSeriesType.SEASON else 'series'
        title = data.get('title') or data.get('name') or 'Channel Series'
        cover = data.get('cover') or data.get('square_cover')
        return SubscriptionMeta(f"{prefix}_{self.target.series_id}", title, cover, self.url)

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        if self.resource_type == ResourceType.FAVORITE_LIST:
            video_urls, latest_video_url, stop_reason = self._get_favlist_videos(context)
        elif self.resource_type == ResourceType.CHANNEL_SERIES:
            video_urls, latest_video_url, stop_reason = self._get_channel_videos(context)
        else:
            video_urls, latest_video_url, stop_reason = self._get_space_videos(context)
        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
        )

    def _get_space_videos(self, context: SubscriptionSyncContext) -> tuple[List[str], Optional[str], str]:
        if not self.target.mid:
            raise ValueError('Missing user id')
        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        limit = resolve_subscription_limit(context)
        page = 1
        page_size = 50

        while True:
            data = fetch_user_videos(self.target.mid, cookies=self.cookies, pn=page, ps=page_size, throttled=True)
            vlist = (data.get('list') or {}).get('vlist') or data.get('vlist') or []
            if not isinstance(vlist, list) or not vlist:
                break

            for v in vlist:
                if v.get("is_union_video") == 1:
                    continue
                bvid = v.get("bvid")
                if bvid:
                    latest_video_url, stop_reason = append_subscription_video_url(
                        f"https://www.bilibili.com/video/{bvid}",
                        video_urls=video_list,
                        context=context,
                        latest_video_url=latest_video_url,
                        limit=limit,
                    )
                    if stop_reason:
                        return video_list, latest_video_url, stop_reason

            if context.mode != 'full':
                break

            page_info = data.get('page') or {}
            total = page_info.get('count') or 0
            if len(video_list) >= total or len(vlist) < page_size:
                break

            page += 1

        return video_list, latest_video_url, 'source_exhausted'

    def _get_favlist_videos(self, context: SubscriptionSyncContext) -> tuple[List[str], Optional[str], str]:
        if not self.target.media_id:
            raise ValueError('Missing favorite list id')

        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        limit = resolve_subscription_limit(context)
        page = 1

        while True:
            data = fetch_fav_resource_list(self.target.media_id, cookies=self.cookies, pn=page, ps=20, throttled=True)
            medias = data.get('medias') or data.get('data', {}).get('medias') or []
            if not medias:
                break

            for media in medias:
                bvid = media.get("bvid")
                if bvid:
                    latest_video_url, stop_reason = append_subscription_video_url(
                        f"https://www.bilibili.com/video/{bvid}",
                        video_urls=video_list,
                        context=context,
                        latest_video_url=latest_video_url,
                        limit=limit,
                    )
                    if stop_reason:
                        return video_list, latest_video_url, stop_reason

            has_more = data.get('has_more', False)
            if context.mode != 'full' or not has_more:
                break
            page += 1

        logger.info('Extracted %s videos from favorite list', len(video_list))
        return video_list, latest_video_url, 'source_exhausted'

    def _get_channel_videos(self, context: SubscriptionSyncContext) -> tuple[List[str], Optional[str], str]:
        if not self.target.series_id:
            raise ValueError('Missing channel series id')
        if not self.target.mid:
            raise ValueError('Missing user id for channel series')
        series_type = self.target.series_type or ChannelSeriesType.SERIES

        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        limit = resolve_subscription_limit(context)
        page = 1
        page_size = 100

        while True:
            data = fetch_series_videos(
                mid=self.target.mid,
                series_id=self.target.series_id,
                series_type=series_type,
                cookies=self.cookies,
                pn=page,
                ps=page_size,
                throttled=True,
            )
            archives = data.get('archives') or (data.get('data') or {}).get('archives') or []
            if not archives and series_type == ChannelSeriesType.SEASON:
                archives = (data.get('archives') or data.get('items') or (data.get('data') or {}).get('archives') or [])
            if not archives:
                break

            for archive in archives:
                bvid = archive.get("bvid") or (archive.get('archive') or {}).get('bvid')
                if bvid:
                    latest_video_url, stop_reason = append_subscription_video_url(
                        f"https://www.bilibili.com/video/{bvid}",
                        video_urls=video_list,
                        context=context,
                        latest_video_url=latest_video_url,
                        limit=limit,
                    )
                    if stop_reason:
                        return video_list, latest_video_url, stop_reason

            if context.mode != 'full' or len(archives) < page_size:
                break

            page += 1

        logger.info('Extracted %s videos from channel series', len(video_list))
        return video_list, latest_video_url, 'source_exhausted'
