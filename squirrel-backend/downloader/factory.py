from downloader.platform.base import Downloader
from sites.bilibili.downloader import BilibiliDownloader
from sites.javdb.downloader import JavdbDownloader
from sites.pornhub.downloader import PornhubDownloader
from sites.youtube.downloader import YoutubeDownloader


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