from sites.downloader import Downloader
from sites.downloader_registry import register_downloader


@register_downloader
class BilibiliDownloader(Downloader):
    domain = 'bilibili.com'

