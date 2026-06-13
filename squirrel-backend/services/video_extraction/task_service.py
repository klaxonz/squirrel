import logging

from sqlalchemy.exc import IntegrityError

from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service
from services.crawl_tasks import service as crawl_task_service
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger(__name__)


class VideoExtractionTaskService:
    def __init__(
        self,
        get_video_by_url=None,
        crawl_tasks=None,
    ):
        self._get_video_by_url = get_video_by_url or video_service.get_video_by_url
        self._crawl_tasks = crawl_tasks or crawl_task_service

    def enqueue(self, params: VideoExtractDto) -> bool:
        domain = extract_top_level_domain(params.url)
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info("Skip enqueue video extraction for disabled site: domain=%s, url=%s", domain, params.url)
            return False

        if params.only_extract:
            video = self._get_video_by_url(params.url)
            if video:
                logger.debug("Video already extracted, skipping: %s", params.url)
                metrics.counter(
                    "crawl.tasks.total",
                    tags={"site": domain, "status": "skipped", "reason": "already_extracted"},
                )
                return False

        return self._create_task(params)

    @staticmethod
    def build_dedupe_key(url: str) -> str:
        return f"dedupe:video_extract:{url}"

    def clear_dedupe(self, params: VideoExtractDto) -> None:
        if params.is_manual:
            return
        self._crawl_tasks.clear_task_dedupe_key(self.build_dedupe_key(params.url))

    def _create_task(self, params: VideoExtractDto) -> bool:
        content = params.model_dump()
        if params.is_manual:
            priority = "manual"
        elif params.is_extract_all:
            priority = "full"
        else:
            priority = "incr"

        domain = extract_top_level_domain(params.url)
        dedupe_key = None if params.is_manual else self.build_dedupe_key(params.url)
        source_type = "manual" if params.is_manual else "scheduled"

        try:
            self._crawl_tasks.create_job_with_task(
                job_type="video_extract",
                source_type=source_type,
                site=domain,
                subscription_id=params.subscription_id,
                priority=priority,
                task_type="video_extract",
                payload=content,
                dedupe_key=dedupe_key,
                video_url=params.url,
                trace_id=params.run_id,
            )
            return True
        except IntegrityError:
            logger.debug("Video extraction task already exists in task store, skipping: %s", params.url)
            metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_in_queue"})
            return False


_default = VideoExtractionTaskService()
enqueue_video_extraction = _default.enqueue
clear_video_extraction_dedupe = _default.clear_dedupe
