"""Video extractor
Handles the core business logic of video extraction

Uses the new Pipeline architecture for video extraction.
"""
import logging
import re

import infrastructure.site_catalog.url as url_helper
import domains.video.application.services.extraction.progress_service as progress_service
from infrastructure.extraction.contracts import ExtractionResult, ExtractionTask, TaskPriority
from infrastructure.extraction.handlers.video_handler import VideoExtractionHandler
from infrastructure.extraction.task_manager import TaskManager
from infrastructure.observability.collector.instance import metrics
from infrastructure.site_catalog.catalog import SiteCatalog
from domains.video.interfaces.dto.dto.video_dto import VideoExtractDto

logger = logging.getLogger(__name__)


class VideoExtractionService:
    def __init__(self):
        self.handler = VideoExtractionHandler()
        self.task_manager = TaskManager()

    @staticmethod
    def _extract_error_type(error_msg: str) -> str:
        if not error_msg:
            return "unknown"

        if ":" in error_msg:
            error_type = error_msg.split(":", maxsplit=1)[0].strip()
            if error_type.endswith("Error") or error_type.endswith("Exception"):
                return error_type
            if "stage" in error_msg.lower():
                match = re.search(r"stage\s*['\"](\w+)['\"]", error_msg.lower())
                if match:
                    return f"Stage:{match.group(1)}"
            if "unsupported" in error_msg.lower():
                return "UnsupportedURL"
            if "timeout" in error_msg.lower():
                return "Timeout"
            if "network" in error_msg.lower() or "connection" in error_msg.lower():
                return "NetworkError"
            return error_type[:50]

        return error_msg[:50] if len(error_msg) > 50 else error_msg

    def extract_video(self, params: VideoExtractDto) -> ExtractionResult:
        domain = url_helper.extract_top_level_domain(params.url)
        tags = {"site": domain}
        extraction_succeeded = False

        try:
            if not SiteCatalog.is_site_enabled(domain=domain):
                logger.info("Skip video extraction because site is disabled: domain=%s, url=%s", domain, params.url)
                metrics.counter("crawl.tasks.total", tags={**tags, "status": "skipped"})
                return ExtractionResult(
                    success=False,
                    error="site_disabled",
                )

            task = self._create_task(params)

            with metrics.timer("crawl.extract", tags=tags):
                logger.debug("Starting video extraction: %s", task.url)
                extraction_result = self.handler.process(task)

            if extraction_result.success:
                extraction_succeeded = True
                video_title = extraction_result.data.title if extraction_result.data else "N/A"
                logger.info("Video extracted: platform=%s, url=%s, title=%s", domain, params.url, video_title)
                metrics.counter("crawl.tasks.total", tags={**tags, "status": "success"})
                metrics.counter("videos.discovered", tags={**tags, "subscribed": str(params.subscribed).lower()})
            else:
                logger.error("Video extraction failed: platform=%s, url=%s, error=%s", domain, params.url, extraction_result.error)
                error_type = self._extract_error_type(extraction_result.error)
                metrics.counter("crawl.tasks.total", tags={**tags, "status": "error"})
                metrics.counter("crawl.errors.total", tags={**tags, "error_type": error_type})

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
