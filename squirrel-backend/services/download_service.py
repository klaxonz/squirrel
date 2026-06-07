import logging

from sqlalchemy.exc import IntegrityError

from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service
from services.crawl_tasks import service as _default_crawl_task_service
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger(__name__)


class DownloadService:
    def __init__(
        self,
        get_video_by_url=None,
        crawl_task_service=None,
    ):
        self._get_video_by_url = get_video_by_url or video_service.get_video_by_url
        self._crawl_task_service = crawl_task_service or _default_crawl_task_service

    def enqueue_video_extraction(self, params: VideoExtractDto) -> bool:
        domain = extract_top_level_domain(params.url)
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info("Skip enqueue video extraction for disabled site: domain=%s, url=%s", domain, params.url)
            return False

        if params.only_extract:
            video = self._get_video_by_url(params.url)
            if video:
                logger.debug("Video already extracted, skipping: %s", params.url)
                metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_extracted"})
                return False

        return self._send_to_extract_queue(params)

    @staticmethod
    def _build_video_dedupe_key(url: str) -> str:
        return f"dedupe:video_extract:{url}"

    def clear_video_extraction_dedupe(self, params: VideoExtractDto) -> None:
        if params.is_manual:
            return
        self._crawl_task_service.clear_task_dedupe_key(self._build_video_dedupe_key(params.url))

    def _send_to_extract_queue(self, params: VideoExtractDto) -> bool:
        content = params.model_dump()
        if params.is_manual:
            priority = "manual"
        elif params.is_extract_all:
            priority = "full"
        else:
            priority = "incr"
        return self._send_to_extract_task(content, params, priority)

    def _send_to_extract_task(self, content: dict, params: VideoExtractDto, priority: str) -> bool:
        domain = extract_top_level_domain(params.url)
        dedupe_key = None if params.is_manual else self._build_video_dedupe_key(params.url)
        source_type = "manual" if params.is_manual else "scheduled"

        try:
            self._crawl_task_service.create_job_with_task(
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


_default = DownloadService()
enqueue_video_extraction = _default.enqueue_video_extraction
clear_video_extraction_dedupe = _default.clear_video_extraction_dedupe
