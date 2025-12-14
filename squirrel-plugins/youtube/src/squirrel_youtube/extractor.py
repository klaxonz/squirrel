"""
YouTube视频提取器
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
    filter_cookies_to_query_string,
    resolve_cookie_file_path,
)

logger = logging.getLogger(__name__)


@register_extractor('youtube', ['youtube.com', 'youtu.be'])
class YoutubeExtractor(YoutubeDLExtractorBase):
    """YouTube视频提取器"""
    
    site_name = 'youtube'
    supported_domains = ['youtube.com', 'youtu.be']
    
    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)
    
    def can_handle(self, url: str) -> bool:
        """检查是否可以处理该URL"""
        if not self.validate_url(url):
            return False
        
        # YouTube特定的URL验证
        return any(pattern in url.lower() for pattern in [
            'youtube.com/watch',
            'youtube.com/shorts',
            'youtu.be/',
            'm.youtube.com'
        ])
    
    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取YouTube视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                
                if video_info:
                    # YouTube特定的信息处理
                    self._process_youtube_info(video_info)
                
                return video_info
                
        except Exception as e:
            logger.error(f"YouTube视频信息提取失败: {url}, error: {e}")
            return None
    
    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """构建yt-dlp选项"""
        cookie_file = resolve_cookie_file_path(url)
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
        }

        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file
        else:
            cookies = filter_cookies_to_query_string(url)
            if cookies:
                ydl_opts['cookie'] = cookies
            
        return ydl_opts
    
    def _process_youtube_info(self, video_info: dict) -> None:
        """处理YouTube特定信息"""
        try:
            if 'timestamp' in video_info:
                # 转成datetime
                video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
            
        except Exception as e:
            logger.warning(f"处理YouTube特定信息失败: {e}")
