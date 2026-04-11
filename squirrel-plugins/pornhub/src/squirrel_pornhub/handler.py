from __future__ import annotations

from typing import Any
from urllib.parse import quote

import phub
from base_api.base import BaseCore
from base_api.modules.config import RuntimeConfig

from crawl import VideoUrlHandler, filter_cookies_to_query_string, get_http_headers


class PornhubHandler:
    """Pornhub视频URL处理器，实现VideoUrlHandler Protocol"""
    
    domain = 'pornhub.com'
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Referer': 'https://www.pornhub.com/',
        'Origin': 'https://www.pornhub.com',
        'Accept-Language': 'en-US,en;q=0.9',
    }

    @staticmethod
    def _parse_cookie_header(cookie_header: str) -> dict[str, str]:
        cookies: dict[str, str] = {}
        for segment in str(cookie_header or '').split(';'):
            item = segment.strip()
            if not item or '=' not in item:
                continue
            name, value = item.split('=', 1)
            normalized_name = name.strip()
            if not normalized_name:
                continue
            cookies[normalized_name] = value.strip()
        return cookies

    def _build_client(self, video_url: str) -> phub.Client:
        config = RuntimeConfig()
        config.timeout = 30
        config.request_delay = 0

        core = BaseCore(config=config)
        client = phub.Client(core=core, login=False, language='en')

        headers = get_http_headers(self.domain, self.default_headers)
        cookie_header = filter_cookies_to_query_string(video_url)
        cookies = self._parse_cookie_header(cookie_header)

        client.core.session.headers.update(headers)
        if cookies:
            client.core.session.cookies.update(cookies)

        return client

    def get_video_url(self, video: Any) -> dict:
        proxy_prefix_path = f"/api/video/proxy?domain=pornhub.com"
        client = self._build_client(video.url)
        video_obj = client.get(video.url)
        video_url = getattr(video_obj, 'get_m3u8_urls', None)
        url = None
        if isinstance(video_url, dict):
            url = next(iter(video_url.values()), None)
        return {
            "video_url": f"{proxy_prefix_path}&url=" + quote(url) if url else None,
            "audio_url": None,
        }


