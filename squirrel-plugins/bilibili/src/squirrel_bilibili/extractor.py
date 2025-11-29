"""
Bilibili视频提取器
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL

from crawl import (
    VideoExtractorBase,
    YoutubeDLExtractorBase,
    register_extractor,
    ExtractionTask,
    ExtractionResult,
    filter_cookies_to_query_string,
    resolve_cookie_file_path,
)

logger = logging.getLogger(__name__)


@register_extractor('bilibili', ['bilibili.com'])
class BilibiliExtractor(YoutubeDLExtractorBase):
    """Bilibili视频提取器"""
    
    test_url = "https://www.bilibili.com"
    
    def __init__(self):
        super().__init__('bilibili', ['bilibili.com'])
    
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
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """执行提取任务"""
        return self.extract_video_info(task)
    
    def _extract_with_ytdlp(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取Bilibili视频信息"""
        try:
            logger.debug(f"开始提取Bilibili视频信息: {url}")
            
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                
                if video_info:
                    # Bilibili特定的信息处理
                    self._process_bilibili_info(video_info)
                
                return video_info
                
        except Exception as e:
            logger.error(f"Bilibili视频信息提取失败: {url}, error: {e}")
            return None
    
    def _build_ytdlp_opts(self, url: str, queue_name: str = None) -> Dict[str, Any]:
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
    
    def _process_bilibili_info(self, video_info: dict) -> None:
        """处理Bilibili特定信息"""
        try:
            if 'timestamp' in video_info:
                # 转换成datetime
                video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])

        except Exception as e:
            logger.warning(f"处理Bilibili特定信息失败: {e}")
