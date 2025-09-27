"""
JavDB视频提取器
"""
import logging
from typing import Dict, Any, Optional

from crawl import (
    VideoExtractorBase,
    register_extractor,
    ExtractionTask,
    ExtractionResult,
)
from .downloader import JavdbDownloader

logger = logging.getLogger(__name__)


@register_extractor('javdb', ['javdb.com'])
class JavdbExtractor(VideoExtractorBase):
    """JavDB视频提取器"""
    
    def __init__(self):
        super().__init__('javdb', ['javdb.com'])
    
    def can_handle(self, url: str) -> bool:
        """检查是否可以处理该URL"""
        if not self.validate_url(url):
            return False
        
        # JavDB特定的URL验证
        return any(pattern in url.lower() for pattern in [
            'javdb.com/v/',
            'javdb.com/video/'
        ])
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """执行提取任务"""
        return self.extract_video_info(task)
    
    def _get_video_info(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """获取JavDB视频信息"""
        try:
            logger.debug(f"开始提取JavDB视频信息: {url}")
            
            # 使用JavDB专用下载器
            javdb_downloader = JavdbDownloader(url)
            video_info = javdb_downloader.get_video_info(queue_name)
            
            if not video_info:
                logger.warning(f"JavDB视频信息提取失败: {url} - 可能需要登录或VIP权限")
                return None
            
            # JavDB特定的信息处理
            self._process_javdb_info(video_info)
            
            return video_info
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'login' in error_msg or '登入' in error_msg:
                logger.warning(f"JavDB视频需要登录访问: {url}")
            elif 'vip' in error_msg:
                logger.warning(f"JavDB视频需要VIP权限: {url}")
            else:
                logger.error(f"JavDB视频信息提取失败: {url}, error: {e}")
            return None
    
    def _process_javdb_info(self, video_info: dict) -> None:
        """处理JavDB特定信息"""
        try:
            # 处理制作商信息
            if 'uploader' in video_info:
                video_info['creator'] = {
                    'name': video_info['uploader'],
                    'id': video_info.get('uploader_id', ''),
                    'url': video_info.get('uploader_url', '')
                }
            
            # 处理分类信息
            if 'categories' in video_info:
                video_info['javdb_categories'] = video_info['categories']
            
            # 处理标签
            if 'tags' in video_info:
                video_info['javdb_tags'] = video_info['tags']
            
            # 处理演员信息
            if 'cast' in video_info:
                video_info['javdb_cast'] = video_info['cast']
            elif 'actors' in video_info:
                video_info['javdb_cast'] = video_info['actors']
            
            # 处理番号信息
            if 'series' in video_info:
                video_info['javdb_series'] = video_info['series']
            
            # 处理发行日期
            if 'release_date' in video_info:
                video_info['javdb_release_date'] = video_info['release_date']
            
            logger.debug(f"JavDB信息处理完成: {video_info.get('title', 'Unknown')}")
            
        except Exception as e:
            logger.warning(f"处理JavDB特定信息失败: {e}")
