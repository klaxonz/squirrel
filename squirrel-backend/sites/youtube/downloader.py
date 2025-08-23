from sites.downloader import Downloader
from sites.downloader_registry import register_downloader


@register_downloader
class YoutubeDownloader(Downloader):
    domain = 'youtube.com'
