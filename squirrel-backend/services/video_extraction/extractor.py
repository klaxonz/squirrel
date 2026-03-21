"""
视频提取器
负责处理视频提取的核心业务逻辑

使用新的Pipeline架构进行视频提取。
"""
import logging
import re
from crawl import ExtractionTask, TaskPriority, ExtractionResult
from schemas.video.dto.video_dto import VideoExtractDto
from core.extraction.handlers.video_handler import VideoExtractionHandler
from core.extraction.task_manager import TaskManager
from utils import url_helper
from utils.site_catalog import SiteCatalog
from utils.metrics import metrics
from services.subscription_sync_event_service import SyncEventInput, append_event
from services.subscription_sync_run_service import SyncEventType, SyncRunStatus
from services import download_service, subscription_sync_state_service

logger = logging.getLogger()
handler = VideoExtractionHandler()
task_manager = TaskManager()


def _extract_error_type(error_msg: str) -> str:
    """从错误消息中提取有意义的错误类型
    
    错误消息格式可能是：
    - "StageExecutionError: Critical stage 'extraction' failed: 140"
    - "Unsupported URL: https://..."
    - "Task processing exception: xxx, error: ..."
    """
    if not error_msg:
        return "unknown"
    
    # 如果包含冒号，提取第一部分作为错误类型
    if ":" in error_msg:
        error_type = error_msg.split(":")[0].strip()
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
    """
    提取视频
    
    Args:
        params: 视频提取参数
        
    Returns:
        ExtractionResult: 提取结果
    
    注意：
        - VIDEO_EXTRACTION_START 事件在入队时由调用方发出
        - VIDEO_EXTRACTION_COMPLETE/ERROR 事件由 VideoExtractionHandler 发出
        - 这里只记录日志，不发出进度事件，避免重复
    """
    domain = url_helper.extract_top_level_domain(params.url)
    tags = {"site": domain}
    
    try:
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info(
                f"Skip video extraction because site is disabled: "
                f"domain={domain}, url={params.url}"
            )
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "skipped"})
            return ExtractionResult(
                success=False,
                error="site_disabled"
            )

        task = _create_task(params)
        
        with metrics.timer("crawl.extract", tags=tags):
            logger.debug(f"Starting video extraction: {task.url}")
            result = handler.process(task)
        
        if result.success:
            video_title = result.data.title if result.data else 'N/A'
            logger.info(
                f"Video extracted: platform={domain}, url={params.url}, "
                f"title={video_title}"
            )
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "success"})
            metrics.counter("videos.discovered", tags={**tags, "subscribed": str(params.subscribed).lower()})
            if params.run_id:
                append_event(
                    SyncEventInput(
                        stream_id=params.run_id,
                        subscription_id=params.subscription_id,
                        sync_state_id=params.sync_state_id,
                        site=domain,
                        sync_mode='full' if params.is_extract_all else 'incremental',
                        trigger=params.trigger or ('manual' if params.is_manual else 'scheduled'),
                        event_type=SyncEventType.VIDEO_EXTRACTED,
                        event_phase='extracting',
                        event_status=SyncRunStatus.RUNNING,
                        payload={'videos_extracted_delta': 1, 'video_url': params.url},
                    )
                )
        else:
            logger.error(
                f"Video extraction failed: platform={domain}, url={params.url}, "
                f"error={result.error}"
            )
            error_type = _extract_error_type(result.error)
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "error"})
            metrics.counter("crawl.errors.total", tags={**tags, "error_type": error_type})
        
        return result
    finally:
        download_service.clear_video_extraction_dedupe(params)
        subscription_sync_state_service.decrement_pending_video_count(params.sync_state_id)


def _create_task(params: VideoExtractDto) -> ExtractionTask:
    priority = TaskPriority.HIGH if params.is_manual else TaskPriority.NORMAL
    
    metadata = {
        'subscription_id': params.subscription_id,
        'sync_state_id': params.sync_state_id,
        'only_extract': params.only_extract,
        'subscribed': params.subscribed,
        'is_extract_all': params.is_extract_all,
        'is_manual': params.is_manual
    }
    
    return task_manager.create_task(
        url=params.url,
        priority=priority,
        metadata=metadata
    )
