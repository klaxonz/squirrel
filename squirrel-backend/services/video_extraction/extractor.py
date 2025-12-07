"""
视频提取器
负责处理视频提取的核心业务逻辑

使用新的Pipeline架构进行视频提取。
"""
import logging
from crawl import ExtractionTask, TaskPriority, ExtractionResult
from schemas.video.dto.video_dto import VideoExtractDto
from core.extraction.handlers.video_handler import VideoExtractionHandler
from core.extraction.task_manager import TaskManager
from utils import url_helper
from utils.site_catalog import SiteCatalog
from utils.metrics import metrics

logger = logging.getLogger()


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
            error_type = result.error or "unknown"
            metrics.counter("crawl.tasks.total", tags={**tags, "status": "error"})
            metrics.counter("crawl.errors.total", tags={**tags, "error_type": error_type})
        
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
