"""
YouTube视频提取器
"""
import logging
from typing import List

from ..factory import register_extractor
from .base_extractor import YoutubeDLExtractor

logger = logging.getLogger(__name__)


@register_extractor('youtube', ['youtube.com', 'youtu.be'])
class YoutubeExtractor(YoutubeDLExtractor):
    """YouTube视频提取器"""
    
    def __init__(self):
        super().__init__('youtube', ['youtube.com', 'youtu.be'])
    
    def validate_url(self, url: str) -> bool:
        """验证YouTube URL格式"""
        if not super().validate_url(url):
            return False
        
        # YouTube特定的URL验证
        return any(pattern in url.lower() for pattern in [
            'youtube.com/watch',
            'youtube.com/shorts',
            'youtu.be/',
            'm.youtube.com'
        ])
    
    def _get_video_info(self, url: str, queue_name: str = None):
        """获取YouTube视频信息"""
        try:
            logger.debug(f"开始提取YouTube视频信息: {url}")
            
            # YouTube不使用Cookie文件
            video_info = super()._get_video_info(url, None)
            
            if video_info:
                # YouTube特定的信息处理
                self._process_youtube_info(video_info)
            
            return video_info
            
        except Exception as e:
            logger.error(f"YouTube视频信息提取失败: {url}, error: {e}")
            return None
    
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


# 自动注册提取器（通过装饰器已经完成）
