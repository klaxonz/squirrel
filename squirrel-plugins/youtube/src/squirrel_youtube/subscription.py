from __future__ import annotations

import re
import logging
from typing import List, Optional

from pytubefix import Channel as YouTubeChannel
from pytubefix import Playlist as YouTubePlaylist

from crawl import (
    SubscriptionMeta,
    SubscriptionSyncContext,
    SubscriptionSyncResult,
    append_subscription_video_url,
    build_subscription_sync_result,
    resolve_subscription_limit,
)

logger = logging.getLogger(__name__)

FULL_SYNC_BATCH_SIZE = 100


class YoutubeSubscription:
    def __init__(self, url: str) -> None:
        self.url = url
        self.is_playlist = self._is_playlist_url(url)
        
        if self.is_playlist:
            self.playlist = YouTubePlaylist(url)
            self.channel = None
        else:
            self.channel = YouTubeChannel(url, use_oauth=False)
            if self.channel:
                channel_id = self.channel.channel_id
                if channel_id:
                    self.url = f"https://www.youtube.com/channel/{channel_id}"
            self.playlist = None
    
    def _is_playlist_url(self, url: str) -> bool:
        """检查URL是否为播放列表"""
        return 'list=' in url or '/playlist?' in url

    def get_subscribe_info(self) -> SubscriptionMeta:
        if self.is_playlist and self.playlist:
            # 播放列表信息
            playlist_id = self._extract_playlist_id(self.url)
            return SubscriptionMeta(
                playlist_id,
                self.playlist.title or "YouTube Playlist",
                None,  # 播放列表没有头像
                self.url,
            )
        else:
            # 频道信息
            return SubscriptionMeta(
                self.channel.channel_id,
                self.channel.channel_name,
                self.channel.thumbnail_url,
                self.url,
            )
    
    def _extract_playlist_id(self, url: str) -> str:
        """从URL中提取播放列表ID"""
        match = re.search(r'list=([^&]+)', url)
        if match:
            return match.group(1)
        return ""

    def sync_videos(self, context: SubscriptionSyncContext) -> SubscriptionSyncResult:
        video_urls, latest_video_url, stop_reason, cursor_payload, has_more = self._collect_videos(context)
        return build_subscription_sync_result(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            context=context,
            stop_reason=stop_reason,
            cursor_payload=cursor_payload,
            has_more=has_more,
        )

    @staticmethod
    def _resolve_resume_offset(context: SubscriptionSyncContext) -> int:
        offset = (context.cursor_payload or {}).get('offset', 0)
        try:
            return max(0, int(offset))
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _resolve_full_sync_batch_limit(context: SubscriptionSyncContext) -> int:
        if context.limit is None:
            return FULL_SYNC_BATCH_SIZE
        try:
            return max(1, int(context.limit))
        except (TypeError, ValueError):
            return FULL_SYNC_BATCH_SIZE

    def _collect_videos(
        self,
        context: SubscriptionSyncContext,
    ) -> tuple[List[str], Optional[str], str, Optional[dict], bool]:
        video_urls: List[str] = []
        latest_video_url: Optional[str] = None
        seen_urls: set[str] = set()
        limit = resolve_subscription_limit(context)
        resume_offset = self._resolve_resume_offset(context) if context.mode == 'full' else 0
        skipped_unique = 0
        batch_limit: Optional[int] = None

        if context.mode == 'full':
            batch_limit = self._resolve_full_sync_batch_limit(context)
            limit = None

        if self.is_playlist and self.playlist:
            try:
                for video in self.playlist.videos:
                    watch_url = getattr(video, 'watch_url', None)
                    if not watch_url:
                        continue
                    if watch_url in seen_urls:
                        continue
                    seen_urls.add(watch_url)
                    if skipped_unique < resume_offset:
                        skipped_unique += 1
                        continue
                    if batch_limit is not None and len(video_urls) >= batch_limit:
                        return (
                            video_urls,
                            latest_video_url,
                            'batch_exhausted',
                            {'offset': resume_offset + len(video_urls)},
                            True,
                        )
                    latest_video_url, stop_reason = append_subscription_video_url(
                        watch_url,
                        video_urls=video_urls,
                        context=context,
                        latest_video_url=latest_video_url,
                        limit=limit,
                    )
                    if stop_reason:
                        return video_urls, latest_video_url, stop_reason, None, False
                logger.info(f"从播放列表提取了 {len(video_urls)} 个视频")
            except Exception as e:
                logger.error(f"提取播放列表视频失败: {e}")
            return video_urls, latest_video_url, 'source_exhausted', None, False

        for source in [self.channel.videos, self.channel.shorts]:
            if not source:
                continue
            for item in source:
                watch_url = getattr(item, 'watch_url', None)
                if not watch_url:
                    continue
                if watch_url in seen_urls:
                    continue
                seen_urls.add(watch_url)
                if skipped_unique < resume_offset:
                    skipped_unique += 1
                    continue
                if batch_limit is not None and len(video_urls) >= batch_limit:
                    return (
                        video_urls,
                        latest_video_url,
                        'batch_exhausted',
                        {'offset': resume_offset + len(video_urls)},
                        True,
                    )
                latest_video_url, stop_reason = append_subscription_video_url(
                    watch_url,
                    video_urls=video_urls,
                    context=context,
                    latest_video_url=latest_video_url,
                    limit=limit,
                )
                if stop_reason:
                    return video_urls, latest_video_url, stop_reason, None, False
        return video_urls, latest_video_url, 'source_exhausted', None, False


