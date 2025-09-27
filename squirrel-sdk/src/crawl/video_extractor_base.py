"""
通用视频提取器基类实现
"""
import logging
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod

from .interfaces import ExtractionTask, ExtractionResult, VideoMeta, IExtractor
from .meta_registry import VideoFactory

logger = logging.getLogger(__name__)


class VideoExtractorBase(IExtractor, ABC):
    """视频提取器基类，提供通用的视频提取功能"""
    
    def __init__(self, site_name: str, supported_domains: List[str]):
        self.site_name = site_name
        self.supported_domains = supported_domains
    
    def validate_url(self, url: str) -> bool:
        """验证URL是否受支持"""
        return any(domain in url.lower() for domain in self.supported_domains)
    
    def can_handle(self, url: str) -> bool:
        """检查是否可以处理该URL - 基础实现使用validate_url"""
        return self.validate_url(url)
    
    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """实现IExtractor接口的extract方法"""
        return self.extract_video_info(task)
    
    def extract_video_info(self, task: ExtractionTask) -> ExtractionResult:
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
            
            # 创建视频实例
            video = self._create_video(task.url, video_info)

            return ExtractionResult(
                success=True,
                data=video,
            )
            
        except Exception as e:
            logger.error(f"视频提取失败: {task.url}, error: {e}", exc_info=True)
            return ExtractionResult(
                success=False,
                error=f"视频提取异常: {str(e)}"
            )
    
    @abstractmethod
    def _get_video_info(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """获取视频信息 - 子类必须实现"""
        pass
    
    def _create_video(self, url: str, video_info: Dict[str, Any]):
        """创建视频实例，使用VideoFactory根据URL域名创建对应的Video子类"""
        try:
            return VideoFactory.create_video(url, video_info)
        except Exception as e:
            logger.error(f"创建视频实例失败: {url}, error: {e}")
            raise
    
    def _is_playlist(self, video_info: Dict[str, Any]) -> bool:
        """检查是否为播放列表"""
        return video_info.get('_type') == 'playlist'


class YoutubeDLExtractorBase(VideoExtractorBase):
    """基于yt-dlp的通用视频提取器基类
    
    注意：这个基类不直接导入yt-dlp，而是期望子类提供具体的实现
    """
    
    def _get_video_info(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取视频信息 - 子类需要提供具体实现"""
        return self._extract_with_ytdlp(url, queue_name)
    
    @abstractmethod 
    def _extract_with_ytdlp(self, url: str, queue_name: str = None) -> Optional[Dict[str, Any]]:
        """子类实现具体的yt-dlp提取逻辑"""
        pass
    
    @abstractmethod
    def _build_ytdlp_opts(self, url: str, queue_name: str = None) -> Dict[str, Any]:
        """构建yt-dlp选项 - 子类实现"""
        pass
