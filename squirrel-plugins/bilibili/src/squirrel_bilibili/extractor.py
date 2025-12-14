import logging
from typing import Optional, Dict, Any, List

from crawl import (
    VideoExtractorBase,
    register_extractor,
    ExtractionTask,
    ExtractionResult,
    VideoMeta,
)
from .api_client import fetch_video_info, build_base_info

logger = logging.getLogger(__name__)


@register_extractor('bilibili', ['bilibili.com', 'b23.tv'])
class BilibiliExtractor(VideoExtractorBase):
    """Bilibili视频提取器（使用 bilibili-api）"""
    
    site_name = 'bilibili'
    supported_domains = ['bilibili.com', 'b23.tv']
    
    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)
    
    def can_handle(self, url: str) -> bool:
        """检查是否可以处理该URL"""
        if not self.validate_url(url):
            return False
        
        # Bilibili特定的URL验证
        return any(pattern in url.lower() for pattern in [
            '/video/bv',
            '/video/av',
            'bilibili.com/video/',
            'b23.tv'
        ])
    
    def _get_video_info(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """使用 bilibili-api 获取视频信息"""
        try:
            info, context, page_info = fetch_video_info(url)
            base_info = build_base_info(info, context, page_info)
            return base_info
        except Exception as e:
            logger.error(f"Bilibili视频信息提取失败: {url}, error: {e}", exc_info=True)
            return None
