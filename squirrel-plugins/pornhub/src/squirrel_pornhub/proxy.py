from __future__ import annotations

from crawl import VideoProxyBase, register_proxy


@register_proxy
class PornhubProxy(VideoProxyBase):
    domain = 'pornhub.com'


