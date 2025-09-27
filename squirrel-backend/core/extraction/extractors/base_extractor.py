"""
基础视频提取器实现
"""
import logging
from typing import Dict, Any, Optional, List
from crawl import ExtractionTask, ExtractionResult
from yt_dlp import YoutubeDL

from core import config
from utils.yt_dlp_helper import build_ydl_opts
from crawl import DownloaderFactory, VideoFactory
from ..base import BaseExtractor

logger = logging.getLogger()


class VideoExtractor(BaseExtractor):
    """视频提取器基类"""
    
    def __init__(self, site_name: str, supported_domains: List[str]):
        super().__init__(site_name, supported_domains)
        self.downloader_factory = DownloaderFactory()
    
    def _do_extract(self, task: ExtractionTask) -> ExtractionResult:
        """执行视频信息提取"""
        try:
            # 获取视频信息
            video_info = self._get_video_info(task.url, task.task_id)
            if not video_info:
                return ExtractionResult(
                    success=False,
                    error="无法获取视频信息或不是有效视频"
                )
            
            # 检查是否为播放列表
            if self._is_playlist(video_info):
                return ExtractionResult(
                    success=False,
                    error="不支持播放列表URL"
                )
            
            # 创建视频元数据（Video 对象）
            video_meta = self._create_video_meta(task.url, video_info)

            return ExtractionResult(
                success=True,
                data=video_meta,
            )
            
        except Exception as e:
            logger.error(f"视频提取失败: {task.url}, error: {e}", exc_info=True)
            return ExtractionResult(
                success=False,
                error=f"视频提取异常: {str(e)}"
            )
    
    def _get_video_info(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """获取视频信息"""
        try:
            downloader = self.downloader_factory.create_downloader(url)
            return downloader.get_video_info(queue_name)
        except Exception as e:
            logger.error(f"获取视频信息失败: {url}, error: {e}")
            return None
    
    def _create_video_meta(self, url: str, video_info: Dict[str, Any]):
        """创建视频元数据"""
        try:
            return VideoFactory.create_video(url, video_info)
        except Exception as e:
            logger.error(f"创建视频元数据失败: {url}, error: {e}")
            raise
    
    def _is_playlist(self, video_info: Dict[str, Any]) -> bool:
        """检查是否为播放列表"""
        return video_info.get('_type') == 'playlist'
    
    def _get_cookie_file(self, queue_name: str = None) -> Optional[str]:
        """获取Cookie文件路径"""
        try:
            return config.get_cookies_file_path_thread(queue_name)
        except Exception as e:
            logger.warning(f"获取Cookie文件失败: {e}")
            return None


class YoutubeDLExtractor(VideoExtractor):
    """基于yt-dlp的通用视频提取器"""
    
    def _get_video_info(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取视频信息"""
        try:
            ydl_opts = build_ydl_opts(url, queue_name, skip_download=True)
            
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                return video_info
                
        except Exception as e:
            logger.error(f"yt-dlp提取视频信息失败: {url}, error: {e}")
            return None
