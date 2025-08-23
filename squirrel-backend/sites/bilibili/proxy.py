from sites.proxy import VideoProxy
from sites.proxy_registry import register_proxy


@register_proxy
class BilibiliProxy(VideoProxy):
    domain = 'bilibili.com'

