from sites.proxy import VideoProxy
from sites.proxy_registry import register_proxy


@register_proxy
class YouTubeProxy(VideoProxy):
    domain = 'youtube.com'

