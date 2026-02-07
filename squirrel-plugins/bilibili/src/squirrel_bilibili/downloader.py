from __future__ import annotations

from typing import Any, Optional

from crawl import Downloader, register_downloader
from .sign import fetch_video_info, build_base_info


@register_downloader
class BilibiliDownloader:
    """Bilibili下载器，实现Downloader Protocol"""
    
    domains = ['bilibili.com']
    domain = 'bilibili.com'
    
    def __init__(self, url: str):
        self.url = url
        self.domain = self.domains[0]

    def get_video_info(self, queue_name: Optional[str] = None) -> Optional[dict]:
        try:
            info, context, page_info = fetch_video_info(self.url)
            base_info = build_base_info(info, context, page_info)
            return base_info
        except Exception:
            return None

    def download(
        self,
        subscription: Any,
        video: Any,
        task: Any,
        queue_thread_name: str,
        video_info: Optional[Any] = None,
    ) -> Any:
        """执行下载工作流"""
        raise NotImplementedError("Download handled by backend download service")
