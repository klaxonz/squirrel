"""
JavDB视频提取器
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from crawl import (
    VideoExtractorBase,
    register_extractor,
    AuthError,
    NotFoundError,
    ParseError,
)
from .downloader import JavdbDownloader

logger = logging.getLogger(__name__)


@register_extractor('javdb', ['javdb.com'])
class JavdbExtractor(VideoExtractorBase):
    """JavDB视频提取器"""

    site_name = 'javdb'
    supported_domains = ['javdb.com']
    url_patterns = [
        'javdb.com/v/',
        'javdb.com/video/'
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _get_video_info(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """获取JavDB视频信息"""
        try:
            javdb_downloader = JavdbDownloader(url)
            video_info = javdb_downloader.get_video_info(queue_name)
            self._process_javdb_info(video_info)
            return video_info

        except (AuthError, NotFoundError, ParseError):
            raise
        except Exception as e:
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if 'login' in error_msg or '登入' in error_msg or '登录' in error_msg:
                raise AuthError(f"需要登录访问: {url}", context=context)
            elif 'vip' in error_msg or '永久vip' in error_msg:
                raise AuthError(f"需要VIP权限: {url}", context=context)
            elif '不存在' in error_msg or '404' in error_msg:
                raise NotFoundError(f"视频不存在: {url}", context=context)
            else:
                logger.error(f"JavDB视频信息提取失败: {url}", exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _process_javdb_info(self, video_info: dict) -> None:
        """处理JavDB特定信息"""
        try:
            if 'timestamp' in video_info:
                if isinstance(video_info['timestamp'], (int, float)):
                    video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
        except Exception as e:
            logger.warning(f"处理JavDB特定信息失败: {e}")
