import logging
from typing import Any

from sites.crawl import (
    SiteError,
    VideoExtractorBase,
)

from .video_api import build_base_info, fetch_video_info

logger = logging.getLogger(__name__)


class BilibiliExtractor(VideoExtractorBase):
    """Bilibili video extractor."""

    site_name = "bilibili"
    supported_domains = ["bilibili.com", "b23.tv"]
    url_patterns = [
        "/video/bv",
        "/video/av",
        "bilibili.com/video/",
        "b23.tv"
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _get_video_info(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """Fetch video metadata from bilibili."""
        try:
            info, context, page_info = fetch_video_info(url)
            base_info = build_base_info(info, context, page_info)
            return base_info
        except SiteError:
            # Typed errors (Auth/NotFound/Network/RateLimit/Parse) raised by
            # api_client's structured translators propagate unchanged; the
            # base extractor turns them into failure results.
            raise
