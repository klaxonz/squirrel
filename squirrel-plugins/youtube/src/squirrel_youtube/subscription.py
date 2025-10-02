from __future__ import annotations

import re
import logging
from typing import List

from pytubefix import Channel as YouTubeChannel
from pytubefix import Playlist as YouTubePlaylist

from crawl import register_subscription, SubscriptionMeta

logger = logging.getLogger(__name__)


@register_subscription("youtube", ["youtube.com", "youtu.be"])
class YoutubeSubscription:
    def __init__(self, url: str) -> None:
        self.url = url
        self.is_playlist = self._is_playlist_url(url)
        
        if self.is_playlist:
            self.playlist = YouTubePlaylist(url)
            self.channel = None
        else:
            self.channel = YouTubeChannel(url, use_oauth=False)
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

    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
        if self.is_playlist and self.playlist:
            # 从播放列表获取视频
            videos_: List[str] = []
            try:
                for video in self.playlist.videos:
                    if video and video.watch_url:
                        videos_.append(video.watch_url)
                logger.info(f"从播放列表提取了 {len(videos_)} 个视频")
            except Exception as e:
                logger.error(f"提取播放列表视频失败: {e}")
            return videos_
        else:
            # 从频道获取视频
            videos_: List[str] = []
            if self.channel.videos:
                for video in self.channel.videos:
                    if video and video.watch_url:
                        videos_.append(video.watch_url)
            shorts_: List[str] = []
            if self.channel.shorts:
                for short in self.channel.shorts:
                    if short and short.watch_url:
                        shorts_.append(short.watch_url)
            return videos_ + shorts_


