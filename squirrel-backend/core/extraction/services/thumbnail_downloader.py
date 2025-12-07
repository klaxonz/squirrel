"""
缩略图下载服务 - 负责异步下载缩略图
"""
import logging

from utils.url_helper import get_site_from_url
from core.site_config_manager import get_effective_site_catalog
from common.site_constants import SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD

logger = logging.getLogger(__name__)


class ThumbnailDownloaderService:
    """
    缩略图下载服务
    
    职责：
    - 检查站点配置
    - 将缩略图下载任务加入队列（异步）
    
    注意：
    - 当前实现为占位符
    - 实际下载逻辑保留在VideoExtractionHandler中
    - 未来可以改为真正的异步队列
    """
    
    def enqueue_download(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str
    ):
        """
        将缩略图下载任务加入队列
        
        Args:
            video_id: 视频ID
            thumbnail_url: 缩略图URL
            site_name: 站点名称
        """
        # 检查站点配置
        if not self._should_download(site_name):
            logger.debug(
                f"Thumbnail download disabled for site: {site_name}"
            )
            return
        
        # TODO: 实现真正的异步下载队列
        # 当前保留原有的同步下载逻辑（在VideoExtractionHandler中）
        logger.debug(
            f"Thumbnail download enqueued: video_id={video_id}, "
            f"url={thumbnail_url[:50]}..."
        )
    
    def _should_download(self, site_name: str) -> bool:
        """检查是否应该下载缩略图"""
        try:
            catalog = get_effective_site_catalog()
            site_info = catalog.get(site_name.lower(), {})
            metadata = site_info.get("metadata", {})
            
            return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD, False)
        
        except Exception as e:
            logger.warning(f"Failed to check thumbnail config: {e}")
            return False


# 单例实例
thumbnail_downloader_service = ThumbnailDownloaderService()
