import logging
from typing import Optional, Dict, Any

from crawl import (
    VideoExtractorBase,
    register_extractor,
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
)
from .sign import fetch_video_info, build_base_info

logger = logging.getLogger(__name__)


@register_extractor('bilibili', ['bilibili.com', 'b23.tv'])
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

    def _get_video_info(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Fetch video metadata from bilibili."""
        try:
            info, context, page_info = fetch_video_info(url)
            base_info = build_base_info(info, context, page_info)
            return base_info
        except Exception as e:
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if '登录' in error_msg or 'login' in error_msg or '会员' in error_msg:
                raise AuthError(f"需要登录或会员权限: {url}", context=context)
            elif '不存在' in error_msg or '已删除' in error_msg or '404' in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif 'timeout' in error_msg or 'connection' in error_msg or '网络' in error_msg:
                raise NetworkError(f"网络连接失败: {url}", context=context)
            else:
                logger.error(f"Bilibili视频信息提取失败: {url}", exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)
