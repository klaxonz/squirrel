"""
YouTube视频提取器
"""
import logging
from typing import Optional, Dict, Any
from yt_dlp import YoutubeDL

from crawl import (
    YoutubeDLExtractorBase,
    register_extractor,
    ExtractionTask,
    ExtractionResult,
)

logger = logging.getLogger(__name__)


@register_extractor('youtube', ['youtube.com', 'youtu.be'])
class YoutubeExtractor(YoutubeDLExtractorBase):
    """YouTube视频提取器"""
    
    def __init__(self):
        super().__init__('youtube', ['youtube.com', 'youtu.be'])
    
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
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """执行提取任务"""
        return self.extract_video_info(task)
    
    def _extract_with_ytdlp(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取YouTube视频信息"""
        try:
            logger.debug(f"开始提取YouTube视频信息: {url}")
            
            # YouTube不使用Cookie文件
            ydl_opts = self._build_ytdlp_opts(url, None)
            
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                
                if video_info:
                    # YouTube特定的信息处理
                    self._process_youtube_info(video_info)
                
                return video_info
                
        except Exception as e:
            logger.error(f"YouTube视频信息提取失败: {url}, error: {e}")
            return None
    
    def _build_ytdlp_opts(self, url: str, queue_name: str = None) -> Dict[str, Any]:
        """构建yt-dlp选项"""
        ydl_opts: Dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
        }
        # YouTube通常不需要额外的配置
        return ydl_opts
    
    def _process_youtube_info(self, video_info: dict) -> None:
        """处理YouTube特定信息"""
        try:
            # 处理频道信息
            if 'channel' in video_info and 'channel_id' in video_info:
                video_info['creator'] = {
                    'name': video_info.get('channel', video_info.get('uploader')),
                    'id': video_info['channel_id'],
                    'url': f"https://www.youtube.com/channel/{video_info['channel_id']}"
                }
            elif 'uploader' in video_info and 'uploader_id' in video_info:
                video_info['creator'] = {
                    'name': video_info['uploader'],
                    'id': video_info['uploader_id'],
                    'url': f"https://www.youtube.com/user/{video_info['uploader_id']}"
                }
            
            # 处理分类信息
            if 'categories' in video_info:
                video_info['youtube_category'] = video_info['categories'][0] if video_info['categories'] else None
            
            # 处理标签
            if 'tags' in video_info:
                video_info['youtube_tags'] = video_info['tags']
            
            # 处理章节信息
            if 'chapters' in video_info:
                video_info['youtube_chapters'] = video_info['chapters']
            
            logger.debug(f"YouTube信息处理完成: {video_info.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"处理YouTube特定信息失败: {e}")
