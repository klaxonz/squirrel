from __future__ import annotations

from domains.subscription.application.services.core.crud import SubscriptionCrudService
from domains.subscription.application.services.core.import_service import SubscriptionImportService
from domains.subscription.application.services.core.listing.service import SubscriptionListService
from domains.subscription.application.services.core.manage import SubscriptionManageService
from domains.subscription.application.services.core.sync.lifecycle import SubscriptionSyncLifecycle
from domains.subscription.application.services.core.update.orchestrator import SubscriptionOrchestrator
from domains.subscription.application.services.core.update.scheduler import SubscriptionScheduler
from domains.subscription.application.services.core.update.strategies.default_strategy import DefaultUpdateStrategy
from domains.subscription.application.services.core.update.video_extraction_coordinator import (
    VideoExtractionCoordinator,
)
from domains.subscription.application.services.crawl.tasks.service import CrawlTaskService
from domains.user.application.services.config import UserConfigService
from domains.video.application.services.service import VideoService
from infrastructure.database.session import get_session


class SubscriptionService:
    """Composition root for subscription application services."""

    def __init__(
        self,
        session_factory=get_session,
        video_service: VideoService | None = None,
        crawl_tasks: CrawlTaskService | None = None,
        user_config: UserConfigService | None = None,
        invalidate_search_suggestions=None,
    ):
        crawl_tasks = crawl_tasks or CrawlTaskService(session_factory=session_factory)
        user_config = user_config or UserConfigService(session_factory=session_factory)
        owns_video_service = video_service is None
        video_service = video_service or VideoService(
            session_factory=session_factory,
            crawl_tasks=crawl_tasks,
            user_config=user_config,
        )
        self.video_service = video_service
        self.crawl_tasks = crawl_tasks
        self.crud = SubscriptionCrudService(
            session_factory=session_factory,
            invalidate_subscription=invalidate_search_suggestions,
        )
        self.lifecycle = SubscriptionSyncLifecycle(
            session_factory=session_factory,
            crud_service=self.crud,
            crawl_tasks=crawl_tasks,
        )
        video_coordinator = VideoExtractionCoordinator(
            lifecycle=self.lifecycle,
            crud_service=video_service.crud,
            persistence_service=video_service.persistence,
            extraction_service=video_service.extraction,
            extraction_task_service=video_service.extraction_tasks,
            session_factory=session_factory,
        )
        self.manage = SubscriptionManageService(
            session_factory=session_factory,
            crud_service=self.crud,
            lifecycle=self.lifecycle,
            crawl_tasks=crawl_tasks,
        )
        self.list = SubscriptionListService(
            session_factory=session_factory,
            get_user_config=user_config.get_config,
        )
        self.orchestrator = SubscriptionOrchestrator(
            session_factory=session_factory,
            lifecycle=self.lifecycle,
            strategy=DefaultUpdateStrategy(
                video_coordinator=video_coordinator,
                listing_service=self.list,
            ),
        )
        self.imports = SubscriptionImportService(
            session_factory=session_factory,
            crud_service=self.crud,
            manage_service=self.manage,
            lifecycle=self.lifecycle,
            crawl_tasks=crawl_tasks,
        )
        self.scheduler = SubscriptionScheduler(
            session_factory=session_factory,
            lifecycle=self.lifecycle,
            orchestrator=self.orchestrator,
        )
        self._owns_video_service = owns_video_service

    @property
    def crud_service(self) -> SubscriptionCrudService:
        return self.crud

    @property
    def import_service(self) -> SubscriptionImportService:
        return self.imports

    @property
    def list_service(self) -> SubscriptionListService:
        return self.list

    @property
    def manage_service(self) -> SubscriptionManageService:
        return self.manage

    @property
    def scheduler_service(self) -> SubscriptionScheduler:
        return self.scheduler

    @property
    def orchestrator_service(self) -> SubscriptionOrchestrator:
        return self.orchestrator
    def close(self) -> None:
        if self._owns_video_service:
            self.video_service.close()
