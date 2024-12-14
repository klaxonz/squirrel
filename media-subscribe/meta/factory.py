from .platforms.bilibili import BilibiliVideo, BilibiliUploader
from .platforms.youtube import YoutubeVideo, YoutubeUploader
from .platforms.pornhub import PornhubVideo, PornhubUploader
from .platforms.javdb import JavVideo, JavUploader

class VideoFactory:
    @staticmethod
    def create_video(url, video_info):
        if 'bilibili.com' in url:
            return BilibiliVideo(url, video_info)
        elif 'youtube.com' in url:
            return YoutubeVideo(url, video_info)
        elif 'pornhub.com' in url:
            return PornhubVideo(url, video_info)
        elif 'javdb.com' in url:
            return JavVideo(url, video_info)

class UploaderFactory:
    @staticmethod
    def create_uploader(url):
        if 'bilibili.com' in url:
            return BilibiliUploader(url)
        elif 'youtube.com' in url:
            return YoutubeUploader(url)
        elif 'pornhub.com' in url:
            return PornhubUploader(url)
        elif 'javdb.com' in url:
            return JavUploader(url) 