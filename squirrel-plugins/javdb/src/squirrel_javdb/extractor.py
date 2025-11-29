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
    
    test_url = "https://javdb.com"
    
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
            # 使用JavDB专用下载器
            javdb_downloader = JavdbDownloader(url)
            video_info = javdb_downloader.get_video_info(queue_name)
            
            if not video_info:
                logger.info(f"JavDB视频信息提取失败: {url} - 可能需要登录或VIP权限")
                return None
            
            # JavDB特定的信息处理
            self._process_javdb_info(video_info)
            
            return video_info
            
        except Exception as e:
            error_msg = str(e).lower()
            if 'login' in error_msg or '登入' in error_msg:
                logger.info(f"JavDB视频需要登录访问: {url}")
            elif 'vip' in error_msg:
                logger.info(f"JavDB视频需要VIP权限: {url}")
            else:
                logger.error(f"JavDB视频信息提取失败: {url}, error: {e}")
            return None
    
    def _process_javdb_info(self, video_info: dict) -> None:
        """处理JavDB特定信息"""
        try:
            # 处理发行日期
            if 'timestamp' in video_info:
                video_info['upload_date'] = video_info['timestamp']
            
        except Exception as e:
            logger.warning(f"处理JavDB特定信息失败: {e}")
