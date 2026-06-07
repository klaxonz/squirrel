import logging
from typing import Any

from crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    VideoExtractorBase,
)

from .video_api import build_base_info, fetch_video_info

logger = logging.getLogger(__name__)


class BilibiliExtractor(VideoExtractorBase):
    """Bilibili video extractor."""

    site_name = 'bilibili'
    supported_domains = ['bilibili.com', 'b23.tv']
    url_patterns = [
        '/video/bv',
        '/video/av',
        'bilibili.com/video/',
        'b23.tv'
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _get_video_info(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """Fetch video metadata from bilibili."""
        try:
            info, context, page_info = fetch_video_info(url)
            base_info = build_base_info(info, context, page_info)
            return base_info
        except Exception as e:  # SDK boundary — translate various errors to domain types
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if '登录' in error_msg or 'login' in error_msg or '会员' in error_msg:
                raise AuthError(f"需要登录或会员权限: {url}", context=context)
            elif '不存在' in error_msg or '已删除' in error_msg or '404' in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif 'timeout' in error_msg or 'connection' in error_msg or '网络' in error_msg:
                raise NetworkError(f"网络连接失败: {url}", context=context)
            elif 'too many requests' in error_msg or 'rate limit' in error_msg or '429' in error_msg:
                raise RateLimitError(f"请求频率过高: {url}", context=context)
            else:
                logger.error(f"Bilibili视频信息提取失败: {url}", exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)
