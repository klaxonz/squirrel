from .base import Video
from sites.bilibili.meta import BilibiliVideo
from sites.javdb.meta import JavVideo
from sites.pornhub.meta import PornhubVideo
from sites.youtube.meta import YoutubeVideo


class VideoFactory:
    @staticmethod
    def create_video(url, video_info) -> Video:
        if 'bilibili.com' in url:
            return BilibiliVideo(url, video_info)
        elif 'youtube.com' in url:
            return YoutubeVideo(url, video_info)
        elif 'pornhub.com' in url:
            return PornhubVideo(url, video_info)
        elif 'javdb.com' in url:
            return JavVideo(url, video_info)
