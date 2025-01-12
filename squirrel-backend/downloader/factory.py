from downloader.platform.base import Downloader
from downloader.platform.bilibili import BilibiliDownloader
from downloader.platform.javdb import JavdbDownloader
from downloader.platform.pornhub import PornhubDownloader
from downloader.platform.youtube import YoutubeDownloader


class DownloaderFactory:

    @staticmethod
    def create_downloader(url: str) -> Downloader:
        if 'bilibili.com' in url:
            return BilibiliDownloader()
        elif 'youtube.com' in url:
            return YoutubeDownloader()
        elif 'pornhub.com' in url:
            return PornhubDownloader()
        elif 'javdb.com' in url:
            return JavdbDownloader()
        else:
            raise ValueError("Invalid url")