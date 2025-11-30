from __future__ import annotations

from typing import Any, Optional
from datetime import datetime

from crawl import BaseDownloader, register_downloader
from .api_client import fetch_video_info, build_base_info


@register_downloader
class BilibiliDownloader(BaseDownloader):
    domain = 'bilibili.com'

    def get_video_info(self, queue_name: Optional[str] = None) -> Optional[dict]:
        try:
            info, context, page_info = fetch_video_info(self.url)
            base_info = build_base_info(info, context, page_info)
            publish_date = base_info.get("publish_date")
            if isinstance(publish_date, (int, float)):
                base_info["publish_date"] = datetime.fromtimestamp(publish_date)
            return base_info
        except Exception:
            return None

    def download(self, subscription, video, task, queue_thread_name: str, video_info=None):  # pragma: no cover
        raise NotImplementedError("Download handled by backend download service")


