from __future__ import annotations

from typing import Optional, Dict, Any

from crawl import Downloader, register_downloader


@register_downloader
class PornhubDownloader:
    """Pornhub下载器，实现Downloader Protocol"""
    
    domains = ['pornhub.com']
    domain = 'pornhub.com'
    
    def __init__(self, url: str):
        self.url = url
        self.domain = self.domains[0]

    def get_video_info(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Placeholder: backend still handles actual download logic.
        # Returning None keeps behaviour aligned with legacy implementation until full migration.
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
