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

logger = logging.getLogger()


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


class VideoExtractor:
    """
    视频提取服务
    
    职责：提供统一的视频提取接口
    使用Pipeline架构处理视频提取流程
    """
    
    def __init__(self):
        self.handler = VideoExtractionHandler()
        self.task_manager = TaskManager()
    
    def extract(self, params: VideoExtractDto) -> ExtractionResult:
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
        
        # 检查站点是否启用
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

        # 创建提取任务
        task = self._create_task(params)
        
        # 使用计时器记录提取耗时（仅记录耗时，不依赖其自动状态记录）
        with metrics.timer("crawl.extract", tags=tags):
            # 使用Pipeline处理
            logger.debug(f"Starting video extraction: {task.url}")
            result = self.handler.process(task)
        
        # 记录结果指标（显式记录成功/失败状态）
        if result.success:
            video_title = result.data.title if result.data else 'N/A'
            logger.info(
                f"Video extracted: platform={domain}, url={params.url}, "
                f"title={video_title}"
            )
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "success"})
            metrics.counter("videos.discovered", tags={**tags, "subscribed": str(params.subscribed).lower()})
        else:
            logger.error(
                f"Video extraction failed: platform={domain}, url={params.url}, "
                f"error={result.error}"
            )
            # 从错误消息中提取错误类型
            error_type = _extract_error_type(result.error)
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "error"})
            metrics.counter("crawl.errors.total", tags={**tags, "error_type": error_type})
            # 注：详细错误信息（含堆栈）已在 pipeline/base.py 中记录
        
        return result
    
    def _create_task(self, params: VideoExtractDto) -> ExtractionTask:
        """创建提取任务"""
        priority = TaskPriority.HIGH if params.is_manual else TaskPriority.NORMAL
        
        metadata = {
            'subscription_id': params.subscription_id,
            'only_extract': params.only_extract,
            'subscribed': params.subscribed,
            'is_extract_all': params.is_extract_all,
            'is_manual': params.is_manual
        }
        
        return self.task_manager.create_task(
            url=params.url,
            priority=priority,
            metadata=metadata
        )


video_extractor = VideoExtractor()
