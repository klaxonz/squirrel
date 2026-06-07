import logging

from sqlalchemy.exc import IntegrityError

from schemas.video.dto.video_dto import VideoExtractDto
from services import video_service
from services.crawl_tasks import service as crawl_task_service
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain

logger = logging.getLogger(__name__)


def enqueue_video_extraction(params: VideoExtractDto) -> bool:
    """将视频提取任务加入队列
    注意：在批量调用时，订阅存在性检查应在外层完成，避免重复查询
    """
    domain = extract_top_level_domain(params.url)
    if not SiteCatalog.is_site_enabled(domain=domain):
        logger.info("Skip enqueue video extraction for disabled site: domain=%s, url=%s", domain, params.url)
        return False

    if params.only_extract:
        video = video_service.get_video_by_url(params.url)
        if video:
            logger.debug("Video already extracted, skipping: %s", params.url)
            metrics.counter("crawl.tasks.total", tags={"site": domain, "status": "skipped", "reason": "already_extracted"})
            return False

    return _send_to_extract_queue(params)


def _build_video_dedupe_key(url: str) -> str:
    return f"dedupe:video_extract:{url}"


def clear_video_extraction_dedupe(params: VideoExtractDto) -> None:
    if params.is_manual:
        return
    crawl_task_service.clear_task_dedupe_key(_build_video_dedupe_key(params.url))


def _send_to_extract_queue(params: VideoExtractDto) -> bool:
    content = params.model_dump()
    if params.is_manual:
        priority = "manual"
    elif params.is_extract_all:
        priority = "full"
    else:
        priority = "incr"
    return _send_to_extract_task(content, params, priority)


def _send_to_extract_task(content: dict, params: VideoExtractDto, priority: str) -> bool:
    domain = extract_top_level_domain(params.url)
    dedupe_key = None if params.is_manual else _build_video_dedupe_key(params.url)
    source_type = "manual" if params.is_manual else "scheduled"

    try:
        crawl_task_service.create_job_with_task(
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


