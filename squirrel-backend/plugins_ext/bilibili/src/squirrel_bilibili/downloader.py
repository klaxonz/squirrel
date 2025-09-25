from __future__ import annotations

from typing import Any, Dict, Optional

from yt_dlp import YoutubeDL

from crawl import BaseDownloader, register_downloader, filter_cookies_to_query_string


@register_downloader
class BilibiliDownloader(BaseDownloader):
    domain = 'bilibili.com'

    def get_video_info(self, queue_name: Optional[str] = None):
        cookies = filter_cookies_to_query_string(self.url)
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
        }
        if cookies:
            ydl_opts['cookie'] = cookies

        with YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(self.url, download=False)

    def download(self, subscription, video, task, queue_thread_name: str, video_info=None):  # pragma: no cover
        raise NotImplementedError("Download handled by backend download service")


