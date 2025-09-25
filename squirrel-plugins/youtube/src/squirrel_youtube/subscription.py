from __future__ import annotations

from typing import List

from pytubefix import Channel as YouTubeChannel

from crawl import register_subscription, SubscriptionMeta


@register_subscription("youtube", ["youtube.com", "youtu.be"])
class YoutubeSubscription:
    def __init__(self, url: str) -> None:
        self.url = url
        self.channel = YouTubeChannel(url, use_oauth=False)

    def get_subscribe_info(self) -> SubscriptionMeta:
        return SubscriptionMeta(
            self.channel.channel_id,
            self.channel.channel_name,
            self.channel.thumbnail_url,
            self.url,
        )

    def get_subscribe_videos(self, extract_all: bool) -> List[str]:
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


