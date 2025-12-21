"""
Pornhub视频提取器
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL

from crawl import (
    YoutubeDLExtractorBase,
    register_extractor,
    filter_cookies_to_query_string,
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
)

logger = logging.getLogger(__name__)


@register_extractor('pornhub', ['pornhub.com'])
class PornhubExtractor(YoutubeDLExtractorBase):
    """Pornhub视频提取器"""

    site_name = 'pornhub'
    supported_domains = ['pornhub.com']
    url_patterns = [
        'pornhub.com/view_video.php',
        'pornhub.com/embed/',
        'pornhub.com/video/'
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取Pornhub视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)

            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)

                if video_info:
                    self._process_pornhub_info(video_info)

                return video_info

        except Exception as e:
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if 'sign in' in error_msg or 'login' in error_msg or 'private' in error_msg:
                raise AuthError(f"需要登录访问: {url}", context=context)
            elif 'unavailable' in error_msg or 'removed' in error_msg or 'deleted' in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif any(kw in error_msg for kw in ['timeout', 'connection', 'network', 'closed file', 'i/o operation']):
                raise NetworkError(f"网络连接失败: {url}", context=context)
            else:
                logger.error(f"Pornhub视频信息提取失败: {url}", exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """构建yt-dlp选项"""
        cookies = filter_cookies_to_query_string(url)
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
            'socket_timeout': 30,
            'retries': 5,
            'extractor_retries': 3,
            'fragment_retries': 5,
            'file_access_retries': 3,
            'ignoreerrors': False,
            'noprogress': True,
        }

        if cookies:
            ydl_opts['cookie'] = cookies

        return ydl_opts

    def _process_pornhub_info(self, video_info: dict) -> None:
        """处理Pornhub特定信息"""
        try:
            if 'timestamp' in video_info:
                video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
        except Exception as e:
            logger.warning(f"处理Pornhub特定信息失败: {e}")
