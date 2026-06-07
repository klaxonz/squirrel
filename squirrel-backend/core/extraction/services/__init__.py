"""提取链路服务层

这些服务负责具体的业务逻辑，被Pipeline Stages调用。
"""

from .actor_processor import ActorProcessorService, actor_processor_service
from .thumbnail_downloader import ThumbnailDownloaderService, thumbnail_downloader_service
from .video_persistence import VideoPersistenceService, video_persistence_service

__all__ = [
    "ActorProcessorService",
    "ThumbnailDownloaderService",
    "VideoPersistenceService",
    "actor_processor_service",
    "thumbnail_downloader_service",
    "video_persistence_service",
]
