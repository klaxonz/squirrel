import time
import random
from pytubefix import Channel as YouTubeChannel
from ..base import BaseSubscribeChannel
from meta.channel import ChannelMeta
from model.channel import Channel

class YouTubeSubscribeChannel(BaseSubscribeChannel):
    DOMAIN = 'youtube.com'

    def __init__(self, url):
        super().__init__(url)
        self.channel = YouTubeChannel(url, use_oauth=False)

    def get_channel_info(self):
        return ChannelMeta(
            self.channel.channel_id,
            self.channel.channel_name,
            self.channel.thumbnail_url,
            self.url
        )

    def get_channel_videos(self, channel: Channel, update_all: bool):
        videos_ = []
        if self.channel.videos:
            for video in self.channel.videos:
                if video and video.watch_url:
                    videos_.append(video.watch_url)
        shorts_ = []
        if self.channel.shorts:
            for short in self.channel.shorts:
                if short and short.watch_url:
                    shorts_.append(short.watch_url)
        return videos_ + shorts_ 