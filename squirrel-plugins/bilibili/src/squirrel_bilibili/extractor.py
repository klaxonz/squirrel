"""
Bilibili视频提取器
"""
import logging
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL

from crawl import (
    VideoExtractorBase, 
    YoutubeDLExtractorBase,
    register_extractor,
    ExtractionTask,
    ExtractionResult,
    filter_cookies_to_query_string
)

logger = logging.getLogger(__name__)


@register_extractor('bilibili', ['bilibili.com'])
class BilibiliExtractor(YoutubeDLExtractorBase):
    """Bilibili视频提取器"""
    
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
        cookies = filter_cookies_to_query_string(url)
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
        }
        
        if cookies:
            ydl_opts['cookie'] = cookies
            
        return ydl_opts
    
    def _process_bilibili_info(self, video_info: dict) -> None:
        """处理Bilibili特定信息"""
        try:
            # 处理UP主信息
            if 'uploader' in video_info and 'uploader_id' in video_info:
                video_info['creator'] = {
                    'name': video_info['uploader'],
                    'id': video_info['uploader_id'],
                    'url': f"https://space.bilibili.com/{video_info['uploader_id']}"
                }
            
            # 处理分区信息
            if 'categories' in video_info:
                video_info['bilibili_category'] = video_info['categories'][0] if video_info['categories'] else None
            
            # 处理标签
            if 'tags' in video_info:
                video_info['bilibili_tags'] = video_info['tags']
            
            logger.debug(f"Bilibili信息处理完成: {video_info.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"处理Bilibili特定信息失败: {e}")
