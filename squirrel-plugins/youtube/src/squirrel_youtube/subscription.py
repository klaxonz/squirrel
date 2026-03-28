from __future__ import annotations

import re
import logging
from typing import List, Optional

from pytubefix import Channel as YouTubeChannel
from pytubefix import Playlist as YouTubePlaylist

from crawl import SubscriptionMeta, SubscriptionSyncContext, SubscriptionSyncResult

logger = logging.getLogger(__name__)


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
        video_urls, latest_video_url, stop_reason = self._collect_videos(context)
        return SubscriptionSyncResult(
            video_urls=video_urls,
            latest_video_url=latest_video_url,
            cursor_payload={'latest_video_url': latest_video_url} if latest_video_url else context.cursor_payload,
            stop_reason=stop_reason,
            total_available=len(video_urls),
        )

    def _collect_videos(self, context: SubscriptionSyncContext) -> tuple[List[str], Optional[str], str]:
        video_urls: List[str] = []
        latest_video_url: Optional[str] = None
        limit = None if context.mode == 'full' else (context.limit or 30)

        if self.is_playlist and self.playlist:
            try:
                for video in self.playlist.videos:
                    watch_url = getattr(video, 'watch_url', None)
                    if not watch_url:
                        continue
                    if latest_video_url is None:
                        latest_video_url = watch_url
                    if context.mode != 'full' and watch_url == context.last_seen_video_url:
                        return video_urls, latest_video_url, 'cursor_hit'
                    video_urls.append(watch_url)
                    if limit is not None and len(video_urls) >= limit:
                        return video_urls, latest_video_url, 'limit_reached'
                logger.info(f"从播放列表提取了 {len(video_urls)} 个视频")
            except Exception as e:
                logger.error(f"提取播放列表视频失败: {e}")
            return video_urls, latest_video_url, 'source_exhausted'

        for source in [self.channel.videos, self.channel.shorts]:
            if not source:
                continue
            for item in source:
                watch_url = getattr(item, 'watch_url', None)
                if not watch_url:
                    continue
                if latest_video_url is None:
                    latest_video_url = watch_url
                if context.mode != 'full' and watch_url == context.last_seen_video_url:
                    return video_urls, latest_video_url, 'cursor_hit'
                video_urls.append(watch_url)
                if limit is not None and len(video_urls) >= limit:
                    return video_urls, latest_video_url, 'limit_reached'
        return video_urls, latest_video_url, 'source_exhausted'


