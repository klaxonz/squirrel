from typing import Dict

from proxy.video_proxy import VideoProxy


class BilibiliProxy(VideoProxy):
    @property
    def headers(self) -> Dict[str, str]:
        return {
            "Referer": "https://www.bilibili.com",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }