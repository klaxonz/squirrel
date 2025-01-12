from .base import Video
from .platforms.bilibili import BilibiliVideo
from .platforms.javdb import JavVideo
from .platforms.pornhub import PornhubVideo
from .platforms.youtube import YoutubeVideo


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
