"""
Bilibili视频提取器
"""
import logging
from typing import List

from ..factory import register_extractor
from .base_extractor import YoutubeDLExtractor

logger = logging.getLogger(__name__)


@register_extractor('bilibili', ['bilibili.com'])
class BilibiliExtractor(YoutubeDLExtractor):
    """Bilibili视频提取器"""
    
    def __init__(self):
        super().__init__('bilibili', ['bilibili.com'])
    
    def validate_url(self, url: str) -> bool:
        """验证Bilibili URL格式"""
        if not super().validate_url(url):
            return False
        
        # Bilibili特定的URL验证
        return any(pattern in url.lower() for pattern in [
            '/video/bv',
            '/video/av',
            'bilibili.com/video/',
            'b23.tv'
        ])
    
    def _get_video_info(self, url: str, queue_name: str = None):
        """获取Bilibili视频信息"""
        try:
            logger.debug(f"开始提取Bilibili视频信息: {url}")
            video_info = super()._get_video_info(url, queue_name)
            
            if video_info:
                # Bilibili特定的信息处理
                self._process_bilibili_info(video_info)
            
            return video_info
            
        except Exception as e:
            logger.error(f"Bilibili视频信息提取失败: {url}, error: {e}")
            return None
    
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


# 自动注册提取器（通过装饰器已经完成）
