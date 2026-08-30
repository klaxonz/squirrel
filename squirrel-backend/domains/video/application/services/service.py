from __future__ import annotations

from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.user.application.services.config import UserConfigService
from domains.video.application.services.creators.service import CreatorService
from domains.video.application.services.crud import VideoCrudService
from domains.video.application.services.engagement.clip_marker import VideoClipMarkerService
from domains.video.application.services.engagement.interaction import VideoInteractionService
from domains.video.application.services.extraction.extractor import VideoExtractionService
from domains.video.application.services.extraction.task_service import VideoExtractionTaskService
from domains.video.application.services.extraction.thumbnail_downloader import ThumbnailDownloaderService
from domains.video.application.services.extraction.video_persistence import VideoPersistenceService
from domains.video.application.services.featured import VideoFeaturedService
from domains.video.application.services.history.service import VideoHistoryService
from domains.video.application.services.listing.page_loader import VideoListPageLoader
from domains.video.application.services.listing.service import VideoListService
from domains.video.application.services.random import VideoRandomService
from domains.video.application.services.search.meili_indexer import get_meili_video_indexer
from infrastructure.config.settings import settings
from infrastructure.database.session import get_session
from infrastructure.extraction.handlers.video_handler import VideoExtractionHandler
from infrastructure.extraction.task_manager import TaskManager


class VideoService:
    """Application composition root for video-facing workflows."""

    def __init__(
        self,
        session_factory=None,
        crawl_tasks: CrawlTaskService | None = None,
        user_config: UserConfigService | None = None,
    ) -> None:
        session_factory = session_factory or get_session
        crawl_tasks = crawl_tasks or CrawlTaskService(session_factory=session_factory)
        user_config = user_config or UserConfigService(session_factory=session_factory)
        self.thumbnail_downloader = ThumbnailDownloaderService()
        meili_indexer = get_meili_video_indexer() if settings.meili.url else None
        self.clip_marker = VideoClipMarkerService(session_factory=session_factory)
        self.persistence = VideoPersistenceService(session_factory=session_factory)
        self.crud = VideoCrudService(session_factory=session_factory)
        self.extraction_tasks = VideoExtractionTaskService(
            get_video_by_url=self.crud.get_video_by_url,
            crawl_tasks=crawl_tasks,
            session_factory=session_factory,
        )
        self.extraction = VideoExtractionService(
            handler=VideoExtractionHandler(
                persistence_service=self.persistence,
                thumbnail_service=self.thumbnail_downloader,
            ),
            task_manager=TaskManager(),
        )
        self.random = VideoRandomService(
            session_factory=session_factory,
            meili_indexer=meili_indexer,
            get_user_config=user_config.get_config,
        )
        self.history = VideoHistoryService(
            session_factory=session_factory,
            get_user_config=user_config.get_config,
            thumbnail_downloader=self.thumbnail_downloader,
        )
        self.interaction = VideoInteractionService(session_factory=session_factory)
        self.creators = CreatorService(session_factory=session_factory)

        page_loader = VideoListPageLoader(self.thumbnail_downloader)
        self.listing = VideoListService(
            session_factory=session_factory,
            get_user_config=user_config.get_config,
            serialize_marker=self.clip_marker.serialize_marker,
            thumbnail_downloader=self.thumbnail_downloader,
            page_loader=page_loader,
            query_service=None,
            meili_indexer=meili_indexer,
        )
        self.featured = VideoFeaturedService(
            session_factory=session_factory,
            page_loader=page_loader,
            thumbnail_downloader=self.thumbnail_downloader,
        )

    def close(self) -> None:
        self.thumbnail_downloader.close()
