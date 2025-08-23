from sites.downloader import Downloader
from sites.downloader_registry import register_downloader


@register_downloader
class PornhubDownloader(Downloader):
    domain = 'pornhub.com'
