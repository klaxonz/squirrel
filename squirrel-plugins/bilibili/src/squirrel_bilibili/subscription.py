from __future__ import annotations

import logging
from typing import List, Optional

from crawl import SubscriptionMeta, SubscriptionSyncContext, SubscriptionSyncResult

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
        return SubscriptionSyncResult(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            cursor_payload={'latest_video_url': latest_video_url} if latest_video_url else context.cursor_payload,
            stop_reason=stop_reason,
            total_available=len(video_urls),
        )

    def _append_video(
        self,
        video_list: List[str],
        video_url: str,
        context: SubscriptionSyncContext,
        latest_video_url: Optional[str],
    ) -> tuple[bool, Optional[str], Optional[str]]:
        latest_video_url = latest_video_url or video_url
        if context.mode != 'full' and video_url == context.last_seen_video_url:
            return False, latest_video_url, 'cursor_hit'
        video_list.append(video_url)
        if context.mode != 'full' and len(video_list) >= (context.limit or 30):
            return False, latest_video_url, 'limit_reached'
        return True, latest_video_url, None

    def _get_space_videos(self, context: SubscriptionSyncContext) -> tuple[List[str], Optional[str], str]:
        if not self.target.mid:
            raise ValueError('Missing user id')
        video_list: List[str] = []
        latest_video_url: Optional[str] = None
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
                    keep_going, latest_video_url, stop_reason = self._append_video(
                        video_list,
                        f"https://www.bilibili.com/video/{bvid}",
                        context,
                        latest_video_url,
                    )
                    if not keep_going:
                        return video_list, latest_video_url, stop_reason or 'cursor_hit'

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
        page = 1

        while True:
            data = fetch_fav_resource_list(self.target.media_id, cookies=self.cookies, pn=page, ps=20, throttled=True)
            medias = data.get('medias') or data.get('data', {}).get('medias') or []
            if not medias:
                break

            for media in medias:
                bvid = media.get("bvid")
                if bvid:
                    keep_going, latest_video_url, stop_reason = self._append_video(
                        video_list,
                        f"https://www.bilibili.com/video/{bvid}",
                        context,
                        latest_video_url,
                    )
                    if not keep_going:
                        return video_list, latest_video_url, stop_reason or 'cursor_hit'

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
                    keep_going, latest_video_url, stop_reason = self._append_video(
                        video_list,
                        f"https://www.bilibili.com/video/{bvid}",
                        context,
                        latest_video_url,
                    )
                    if not keep_going:
                        return video_list, latest_video_url, stop_reason or 'cursor_hit'

            if context.mode != 'full' or len(archives) < page_size:
                break

            page += 1

        logger.info('Extracted %s videos from channel series', len(video_list))
        return video_list, latest_video_url, 'source_exhausted'
