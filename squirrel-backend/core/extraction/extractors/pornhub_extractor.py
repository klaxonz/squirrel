"""
Pornhub视频提取器
"""
import logging
from typing import List

from ..factory import register_extractor
from .base_extractor import YoutubeDLExtractor

logger = logging.getLogger()


@register_extractor('pornhub', ['pornhub.com'])
class PornhubExtractor(YoutubeDLExtractor):
    """Pornhub视频提取器"""
    
    def __init__(self):
        super().__init__('pornhub', ['pornhub.com'])
    
    def validate_url(self, url: str) -> bool:
        """验证Pornhub URL格式"""
        if not super().validate_url(url):
            return False
        
        # Pornhub特定的URL验证
        return any(pattern in url.lower() for pattern in [
            'pornhub.com/view_video.php',
            'pornhub.com/embed/',
            'pornhub.com/video/'
        ])
    
    def _get_video_info(self, url: str, queue_name: str = None):
        """获取Pornhub视频信息"""
        try:
            logger.debug(f"开始提取Pornhub视频信息: {url}")
            video_info = super()._get_video_info(url, queue_name)
            
            if video_info:
                # Pornhub特定的信息处理
                self._process_pornhub_info(video_info)
            
            return video_info
            
        except Exception as e:
            logger.error(f"Pornhub视频信息提取失败: {url}, error: {e}")
            return None
    
    def _process_pornhub_info(self, video_info: dict) -> None:
        """处理Pornhub特定信息"""
        try:
            # 处理上传者信息
            if 'uploader' in video_info:
                video_info['creator'] = {
                    'name': video_info['uploader'],
                    'id': video_info.get('uploader_id', ''),
                    'url': video_info.get('uploader_url', '')
                }
            
            # 处理分类信息
            if 'categories' in video_info:
                video_info['pornhub_categories'] = video_info['categories']
            
            # 处理标签
            if 'tags' in video_info:
                video_info['pornhub_tags'] = video_info['tags']
            
            # 处理演员信息
            if 'cast' in video_info:
                video_info['pornhub_cast'] = video_info['cast']
            
            # 处理观看次数
            if 'view_count' in video_info:
                video_info['pornhub_views'] = video_info['view_count']
            
            logger.debug(f"Pornhub信息处理完成: {video_info.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"处理Pornhub特定信息失败: {e}")


# 自动注册提取器（通过装饰器已经完成）
