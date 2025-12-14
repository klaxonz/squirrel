from __future__ import annotations

from typing import Any
from urllib.parse import quote

import phub

from crawl import VideoUrlHandler, register_handler


@register_handler
class PornhubHandler:
    """Pornhub视频URL处理器，实现VideoUrlHandler Protocol"""
    
    domain = 'pornhub.com'

    def get_video_url(self, video: Any) -> dict:
        proxy_prefix_path = f"/api/video/proxy?domain=pornhub.com"
        client = phub.Client()
        video_obj = client.get(video.url)
        video_url = getattr(video_obj, 'get_m3u8_urls', None)
        url = None
        if isinstance(video_url, dict):
            url = next(iter(video_url.values()), None)
        return {
            "video_url": f"{proxy_prefix_path}&url=" + quote(url) if url else None,
            "audio_url": None,
        }


