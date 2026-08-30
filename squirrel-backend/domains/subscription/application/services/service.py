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
from domains.video.application.services.service import VideoService
from infrastructure.database.session import get_session


class SubscriptionService:
    """Composition root for subscription application services."""

    def __init__(self, session_factory=get_session, video_service: VideoService | None = None):
        video_service = video_service or VideoService(session_factory=session_factory)
        self.crud = SubscriptionCrudService(session_factory=session_factory)
        self.lifecycle = SubscriptionSyncLifecycle(
            session_factory=session_factory,
            crud_service=self.crud,
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
        )
        self.list = SubscriptionListService(session_factory=session_factory)
        self.orchestrator = SubscriptionOrchestrator(
            session_factory=session_factory,
            lifecycle=self.lifecycle,
            strategy=DefaultUpdateStrategy(
                video_coordinator=video_coordinator,
                session_factory=session_factory,
                listing_service=self.list,
            ),
        )
        self.imports = SubscriptionImportService(
            session_factory=session_factory,
            crud_service=self.crud,
            manage_service=self.manage,
            lifecycle=self.lifecycle,
        )
        self.scheduler = SubscriptionScheduler(
            session_factory=session_factory,
            lifecycle=self.lifecycle,
            orchestrator=self.orchestrator,
        )
        self.video_service = video_service

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
        self.video_service.close()
