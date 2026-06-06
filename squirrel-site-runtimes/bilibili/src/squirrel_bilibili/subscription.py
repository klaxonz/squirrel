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
HEAD_SAMPLE_LIMIT = 10


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
            video_urls, latest_video_url, stop_reason, cursor_payload, has_more, result_kwargs = self._get_favlist_videos(context)
        elif self.resource_type == ResourceType.CHANNEL_SERIES:
            video_urls, latest_video_url, stop_reason, cursor_payload, has_more, result_kwargs = self._get_channel_videos(context)
        else:
            video_urls, latest_video_url, stop_reason, cursor_payload, has_more, result_kwargs = self._get_space_videos(context)
        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
            cursor_payload=cursor_payload,
            has_more=has_more,
            **result_kwargs,
        )

    @staticmethod
    def _append_head_sample(head_sample_urls: list[str], video_url: str) -> None:
        if video_url in head_sample_urls or len(head_sample_urls) >= HEAD_SAMPLE_LIMIT:
            return
        head_sample_urls.append(video_url)

    @staticmethod
    def _build_result_kwargs(
        context: SubscriptionSyncContext,
        *,
        head_sample_urls: list[str],
        anchor_found: bool | None,
        total_available: Optional[int],
    ) -> dict:
        if context.mode == 'full':
            return {'total_available': total_available}
        return {
            'head_sample_urls': list(head_sample_urls),
            'anchor_found': anchor_found,
            'total_available': total_available,
        }

    @staticmethod
    def _resolve_page(context: SubscriptionSyncContext) -> int:
        page = (context.cursor_payload or {}).get('page', 1)
        try:
            return max(1, int(page))
        except (TypeError, ValueError):
            return 1

    def _get_space_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[List[str], Optional[str], str, Optional[dict], bool, dict]:
        if not self.target.mid:
            raise ValueError('Missing user id')
        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        head_sample_urls: List[str] = []
        limit = resolve_subscription_limit(context)
        page = self._resolve_page(context)
        page_size = 50

        data = fetch_user_videos(self.target.mid, cookies=self.cookies, pn=page, ps=page_size, throttled=True)
        page_info = data.get('page') or {}
        total_available = page_info.get('count')
        vlist = (data.get('list') or {}).get('vlist') or data.get('vlist') or []
        if not isinstance(vlist, list) or not vlist:
            return (
                video_list,
                latest_video_url,
                'source_exhausted',
                None,
                False,
                self._build_result_kwargs(
                    context,
                    head_sample_urls=head_sample_urls,
                    anchor_found=False if context.last_seen_video_url else None,
                    total_available=total_available,
                ),
            )

        for v in vlist:
            if v.get('is_union_video') == 1:
                continue
            bvid = v.get('bvid')
            if bvid:
                video_url = f'https://www.bilibili.com/video/{bvid}'
                self._append_head_sample(head_sample_urls, video_url)
                latest_video_url, stop_reason = append_subscription_video_url(
                    video_url,
                    video_urls=video_list,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=limit,
                )
                if stop_reason:
                    return (
                        video_list,
                        latest_video_url,
                        stop_reason,
                        None,
                        False,
                        self._build_result_kwargs(
                            context,
                            head_sample_urls=head_sample_urls,
                            anchor_found=True if stop_reason == 'cursor_hit' else None,
                            total_available=total_available,
                        ),
                    )

        if context.mode == 'full':
            total = total_available or 0
            has_more = bool(total and page * page_size < total) or len(vlist) >= page_size
            if has_more:
                return (
                    video_list,
                    latest_video_url,
                    'batch_exhausted',
                    {'page': page + 1},
                    True,
                    {'total_available': total_available},
                )

        return (
            video_list,
            latest_video_url,
            'source_exhausted',
            None,
            False,
            self._build_result_kwargs(
                context,
                head_sample_urls=head_sample_urls,
                anchor_found=False if context.mode != 'full' and context.last_seen_video_url else None,
                total_available=total_available,
            ),
        )

    def _get_favlist_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[List[str], Optional[str], str, Optional[dict], bool, dict]:
        if not self.target.media_id:
            raise ValueError('Missing favorite list id')

        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        head_sample_urls: List[str] = []
        limit = resolve_subscription_limit(context)
        page = self._resolve_page(context)
        data = fetch_fav_resource_list(self.target.media_id, cookies=self.cookies, pn=page, ps=20, throttled=True)
        total_available = (
            (data.get('info') or {}).get('media_count')
            or ((data.get('data') or {}).get('info') or {}).get('media_count')
        )
        medias = data.get('medias') or data.get('data', {}).get('medias') or []
        if not medias:
            return (
                video_list,
                latest_video_url,
                'source_exhausted',
                None,
                False,
                self._build_result_kwargs(
                    context,
                    head_sample_urls=head_sample_urls,
                    anchor_found=False if context.last_seen_video_url else None,
                    total_available=total_available,
                ),
            )

        for media in medias:
            bvid = media.get('bvid')
            if bvid:
                video_url = f'https://www.bilibili.com/video/{bvid}'
                self._append_head_sample(head_sample_urls, video_url)
                latest_video_url, stop_reason = append_subscription_video_url(
                    video_url,
                    video_urls=video_list,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=limit,
                )
                if stop_reason:
                    return (
                        video_list,
                        latest_video_url,
                        stop_reason,
                        None,
                        False,
                        self._build_result_kwargs(
                            context,
                            head_sample_urls=head_sample_urls,
                            anchor_found=True if stop_reason == 'cursor_hit' else None,
                            total_available=total_available,
                        ),
                    )

        has_more = data.get('has_more', False)
        if context.mode == 'full' and has_more:
            return (
                video_list,
                latest_video_url,
                'batch_exhausted',
                {'page': page + 1},
                True,
                {'total_available': total_available},
            )

        logger.info('Extracted %s videos from favorite list', len(video_list))
        return (
            video_list,
            latest_video_url,
            'source_exhausted',
            None,
            False,
            self._build_result_kwargs(
                context,
                head_sample_urls=head_sample_urls,
                anchor_found=False if context.mode != 'full' and context.last_seen_video_url else None,
                total_available=total_available,
            ),
        )

    def _get_channel_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[List[str], Optional[str], str, Optional[dict], bool, dict]:
        if not self.target.series_id:
            raise ValueError('Missing channel series id')
        if not self.target.mid:
            raise ValueError('Missing user id for channel series')
        series_type = self.target.series_type or ChannelSeriesType.SERIES

        video_list: List[str] = []
        latest_video_url: Optional[str] = None
        head_sample_urls: List[str] = []
        limit = resolve_subscription_limit(context)
        page = self._resolve_page(context)
        page_size = 100

        data = fetch_series_videos(
            mid=self.target.mid,
            series_id=self.target.series_id,
            series_type=series_type,
            cookies=self.cookies,
            pn=page,
            ps=page_size,
            throttled=True,
        )
        total_available = (
            (data.get('page') or {}).get('total')
            or (data.get('meta') or {}).get('total')
            or (data.get('data') or {}).get('total')
        )
        archives = data.get('archives') or (data.get('data') or {}).get('archives') or []
        if not archives and series_type == ChannelSeriesType.SEASON:
            archives = data.get('archives') or data.get('items') or (data.get('data') or {}).get('archives') or []
        if not archives:
            return (
                video_list,
                latest_video_url,
                'source_exhausted',
                None,
                False,
                self._build_result_kwargs(
                    context,
                    head_sample_urls=head_sample_urls,
                    anchor_found=False if context.last_seen_video_url else None,
                    total_available=total_available,
                ),
            )

        for archive in archives:
            bvid = archive.get('bvid') or (archive.get('archive') or {}).get('bvid')
            if bvid:
                video_url = f'https://www.bilibili.com/video/{bvid}'
                self._append_head_sample(head_sample_urls, video_url)
                latest_video_url, stop_reason = append_subscription_video_url(
                    video_url,
                    video_urls=video_list,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=limit,
                )
                if stop_reason:
                    return (
                        video_list,
                        latest_video_url,
                        stop_reason,
                        None,
                        False,
                        self._build_result_kwargs(
                            context,
                            head_sample_urls=head_sample_urls,
                            anchor_found=True if stop_reason == 'cursor_hit' else None,
                            total_available=total_available,
                        ),
                    )

        if context.mode == 'full' and len(archives) >= page_size:
            return (
                video_list,
                latest_video_url,
                'batch_exhausted',
                {'page': page + 1},
                True,
                {'total_available': total_available},
            )

        logger.info('Extracted %s videos from channel series', len(video_list))
        return (
            video_list,
            latest_video_url,
            'source_exhausted',
            None,
            False,
            self._build_result_kwargs(
                context,
                head_sample_urls=head_sample_urls,
                anchor_found=False if context.mode != 'full' and context.last_seen_video_url else None,
                total_available=total_available,
            ),
        )
