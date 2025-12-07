"""
提取链路服务层

这些服务负责具体的业务逻辑，被Pipeline Stages调用。
"""

from .video_persistence import VideoPersistenceService, video_persistence_service
from .actor_processor import ActorProcessorService, actor_processor_service
from .thumbnail_downloader import ThumbnailDownloaderService, thumbnail_downloader_service
from .download_task_creator import DownloadTaskCreatorService, download_task_creator_service

__all__ = [
    'VideoPersistenceService',
    'ActorProcessorService',
    'ThumbnailDownloaderService',
    'DownloadTaskCreatorService',
    'video_persistence_service',
    'actor_processor_service',
    'thumbnail_downloader_service',
    'download_task_creator_service',
]
