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
    
    def __init__(self):
        super().__init__('pornhub', ['pornhub.com'])
    
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
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """执行提取任务"""
        return self.extract_video_info(task)
    
    def _extract_with_ytdlp(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取Pornhub视频信息"""
        try:
            logger.debug(f"开始提取Pornhub视频信息: {url}")
            
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
    
    def _build_ytdlp_opts(self, url: str, queue_name: str = None) -> Dict[str, Any]:
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

            logger.info(f"Pornhub信息处理完成: {video_info.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"处理Pornhub特定信息失败: {e}")
