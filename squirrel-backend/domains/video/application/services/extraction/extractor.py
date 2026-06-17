"""Video extractor
Handles the core business logic of video extraction

Uses the new Pipeline architecture for video extraction.
"""
import logging

import domains.video.application.services.extraction.progress_service as progress_service
import infrastructure.site_catalog.url as url_helper
from domains.video.interfaces.dto.video_dto import VideoExtractDto
from infrastructure.extraction.contracts import ExtractionResult, ExtractionTask, TaskPriority
from infrastructure.extraction.handlers.video_handler import VideoExtractionHandler
from infrastructure.extraction.task_manager import TaskManager
from infrastructure.site_catalog.catalog import SiteCatalog

logger = logging.getLogger(__name__)


class VideoExtractionService:
    def __init__(self):
        self.handler = VideoExtractionHandler()
        self.task_manager = TaskManager()

    def extract_video(self, params: VideoExtractDto) -> ExtractionResult:
        domain = url_helper.extract_top_level_domain(params.url)
        extraction_succeeded = False

        try:
            if not SiteCatalog.is_site_enabled(domain=domain):
                logger.info("Skip video extraction because site is disabled: domain=%s, url=%s", domain, params.url)
                return ExtractionResult(
                    success=False,
                    error="site_disabled",
                )

            task = self._create_task(params)

            logger.debug("Starting video extraction: %s", task.url)
            extraction_result = self.handler.process(task)

            if extraction_result.success:
                extraction_succeeded = True
                video_title = extraction_result.data.title if extraction_result.data else "N/A"
                logger.info("Video extracted: platform=%s, url=%s, title=%s", domain, params.url, video_title)
            else:
                logger.error("Video extraction failed: platform=%s, url=%s, error=%s", domain, params.url, extraction_result.error)

            return extraction_result
        finally:
            progress_service.record_finished(params, succeeded=extraction_succeeded, site=domain)

    def _create_task(self, params: VideoExtractDto) -> ExtractionTask:
        priority = TaskPriority.HIGH if params.is_manual else TaskPriority.NORMAL

        metadata = {
            "subscription_id": params.subscription_id,
            "sync_state_id": params.sync_state_id,
            "only_extract": params.only_extract,
            "subscribed": params.subscribed,
            "sync_mode": "full" if params.is_extract_all else "incremental",
            "is_extract_all": params.is_extract_all,
            "is_manual": params.is_manual,
        }

        return self.task_manager.create_task(
            url=params.url,
            priority=priority,
            metadata=metadata,
        )


video_extraction_service = VideoExtractionService()
extract_video = video_extraction_service.extract_video
