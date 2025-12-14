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
    ExtractionTask,
    ExtractionResult,
    filter_cookies_to_query_string
)

logger = logging.getLogger(__name__)


@register_extractor('pornhub', ['pornhub.com'])
class PornhubExtractor(YoutubeDLExtractorBase):
    """Pornhub视频提取器"""
    
    site_name = 'pornhub'
    supported_domains = ['pornhub.com']
    
    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)
    
    def can_handle(self, url: str) -> bool:
        """检查是否可以处理该URL"""
        if not self.validate_url(url):
            return False
        
        # Pornhub特定的URL验证
        return any(pattern in url.lower() for pattern in [
            'pornhub.com/view_video.php',
            'pornhub.com/embed/',
            'pornhub.com/video/'
        ])
    
    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取Pornhub视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                
                if video_info:
                    # Pornhub特定的信息处理
                    self._process_pornhub_info(video_info)
                
                return video_info
                
        except Exception as e:
            logger.error(f"Pornhub视频信息提取失败: {url}, error: {e}")
            return None
    
    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """构建yt-dlp选项"""
        cookies = filter_cookies_to_query_string(url)
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
        }
        
        if cookies:
            ydl_opts['cookie'] = cookies
            
        return ydl_opts
    
    def _process_pornhub_info(self, video_info: dict) -> None:
        """处理Pornhub特定信息"""
        try:
            # 处理上传者信息
            if 'timestamp' in video_info:
                # 转成datetime
                video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])

        except Exception as e:
            logger.warning(f"处理Pornhub特定信息失败: {e}")
