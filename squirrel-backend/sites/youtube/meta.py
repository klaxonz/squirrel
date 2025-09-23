from pytubefix import YouTube

from crawl import Actor, Video
from sites.meta_registry import register_meta


@register_meta
class YoutubeVideo(Video):
    domain = 'youtube.com'

    def __init__(self, url, base_info):
        super().__init__(url, base_info)

    @property
    def actors(self):
        if len(self._actors) == 0:
            video = YouTube(self.url, use_oauth=False, allow_oauth_cache=False)
            actor = Actor(video.channel_url)
            actor.name = video.author
            actor.avatar = video.thumbnail_url
            self._actors.append(actor)
        return self._actors
