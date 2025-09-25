from __future__ import annotations

from typing import Optional, Dict, Any

from crawl import BaseDownloader, register_downloader


@register_downloader
class PornhubDownloader(BaseDownloader):
    domain = 'pornhub.com'

    def get_video_info(self, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        # Placeholder: backend still handles actual download logic.
        # Returning None keeps behaviour aligned with legacy implementation until full migration.
        return None

    def download(self, subscription, video, task, queue_thread_name: str, video_info=None):  # pragma: no cover
        raise NotImplementedError("Download handled by backend download service")
