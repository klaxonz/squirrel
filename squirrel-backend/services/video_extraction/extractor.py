"""Video extractor
Handles the core business logic of video extraction

Uses the new Pipeline architecture for video extraction.
"""
import logging
import re

from core.extraction.contracts import ExtractionResult, ExtractionTask, TaskPriority
from core.extraction.handlers.video_handler import VideoExtractionHandler
from core.extraction.task_manager import TaskManager
from schemas.video.dto.video_dto import VideoExtractDto
from services import download_service, subscription_sync_state_service
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncRunStatus
from utils import url_helper
from utils.metrics import metrics
from utils.site_catalog import SiteCatalog

logger = logging.getLogger(__name__)
handler = VideoExtractionHandler()
task_manager = TaskManager()


def _extract_error_type(error_msg: str) -> str:
    """Extract meaningful error type from error message

    Error message format may be:
    - "StageExecutionError: Critical stage 'extraction' failed: 140"
    - "Unsupported URL: https://..."
    - "Task processing exception: xxx, error: ..."
    """
    if not error_msg:
        return "unknown"

    # 如果包含冒号，提取第一部分作为错误类型
    if ":" in error_msg:
        error_type = error_msg.split(":", maxsplit=1)[0].strip()
        # 如果是常见的异常类型名称，直接返回
        if error_type.endswith("Error") or error_type.endswith("Exception"):
            return error_type
        # 如果是描述性文本，尝试提取关键信息
        if "stage" in error_msg.lower():
            # 提取阶段名称，如 "extraction", "persistence"
            match = re.search(r"stage\s*['\"](\w+)['\"]", error_msg.lower())
            if match:
                return f"Stage:{match.group(1)}"
        if "unsupported" in error_msg.lower():
            return "UnsupportedURL"
        if "timeout" in error_msg.lower():
            return "Timeout"
        if "network" in error_msg.lower() or "connection" in error_msg.lower():
            return "NetworkError"
        return error_type[:50]  # 截断过长的类型名

    # 没有冒号，返回前50个字符
    return error_msg[:50] if len(error_msg) > 50 else error_msg


def extract_video(params: VideoExtractDto) -> ExtractionResult:
    """Extract video

    Args:
        params: Video extraction parameters

    Returns:
        ExtractionResult: Extraction result

    Note:
        - VIDEO_EXTRACTION_START event is emitted by the caller when enqueuing
        - VIDEO_EXTRACTION_COMPLETE/ERROR events are emitted by VideoExtractionHandler
        - Only log here, do not emit progress events to avoid duplication

    """
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

        task = _create_task(params)

        with metrics.timer("crawl.extract", tags=tags):
            logger.debug("Starting video extraction: %s", task.url)
            result = handler.process(task)

        if result.success:
            extraction_succeeded = True
            video_title = result.data.title if result.data else "N/A"
            logger.info("Video extracted: platform=%s, url=%s, title=%s", domain, params.url, video_title)
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "success"})
            metrics.counter("videos.discovered", tags={**tags, "subscribed": str(params.subscribed).lower()})
            if params.run_id:
                append_event(
                    SyncEventInput(
                        stream_id=params.run_id,
                        subscription_id=params.subscription_id,
                        sync_state_id=params.sync_state_id,
                        site=domain,
                        sync_mode="full" if params.is_extract_all else "incremental",
                        trigger=params.trigger or ("manual" if params.is_manual else "scheduled"),
                        event_type=SyncEventType.VIDEO_EXTRACTED,
                        event_phase="extracting",
                        event_status=SyncRunStatus.RUNNING,
                        payload={"videos_extracted_delta": 1, "video_url": params.url},
                    ),
                )
        else:
            logger.error("Video extraction failed: platform=%s, url=%s, error=%s", domain, params.url, result.error)
            error_type = _extract_error_type(result.error)
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "error"})
            metrics.counter("crawl.errors.total", tags={**tags, "error_type": error_type})

        return result
    finally:
        download_service.clear_video_extraction_dedupe(params)
        subscription_sync_state_service.decrement_pending_video_count(
            params.sync_state_id,
            run_id=params.run_id,
            trigger=params.trigger or ("manual" if params.is_manual else "scheduled"),
            allow_completion=extraction_succeeded,
        )


def _create_task(params: VideoExtractDto) -> ExtractionTask:
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

    return task_manager.create_task(
        url=params.url,
        priority=priority,
        metadata=metadata,
    )
