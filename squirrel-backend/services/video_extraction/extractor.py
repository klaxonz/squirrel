"""
视频提取器
负责处理视频提取的核心业务逻辑
"""
import logging
from crawl import ExtractionTask, TaskPriority
from schemas.video.dto.video_dto import VideoExtractDto
from core.extraction.task_manager import TaskManager
from core.extraction.handlers.video_handler import VideoExtractionHandler
from core.extraction.base import BaseTaskProcessor
from core.extraction.factory import get_extractor_factory
from utils import url_helper
from utils.site_catalog import SiteCatalog

logger = logging.getLogger()


class VideoTaskProcessor(BaseTaskProcessor):
    """视频任务处理器"""

    def __init__(self):
        extractor_factory = get_extractor_factory()
        video_handler = VideoExtractionHandler()
        super().__init__(None, video_handler)
        self.extractor_factory = extractor_factory

    def _get_extractor_for_task(self, task: ExtractionTask):
        return self.extractor_factory.create_extractor(task.url)

    def can_process(self, task: ExtractionTask) -> bool:
        """检查是否可以处理任务"""
        extractor = self.extractor_factory.create_extractor(task.url)
        return extractor is not None

    def process(self, task: ExtractionTask):
        """处理任务"""
        extractor = self._get_extractor_for_task(task)
        if not extractor:
            from crawl import ExtractionResult
            result = ExtractionResult(
                success=False,
                error=f"未找到合适的提取器: {task.url}"
            )
            self.result_handler.handle_failure(task, result)
            return result

        return super()._process_with_extractor(extractor, task)


class VideoExtractor:
    """
    视频提取服务
    职责：提供统一的视频提取接口
    """
    
    def __init__(self):
        self.task_manager = TaskManager()
        self.processor = VideoTaskProcessor()
        self.task_manager.add_processor(self.processor)
    
    def extract(self, params: VideoExtractDto):
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
        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info(f"Skip video extraction because site is disabled: domain={domain}, url={params.url}")
            from crawl import ExtractionResult
            return ExtractionResult(
                success=False,
                error="site_disabled"
            )

        task = self._create_task(params)
        result = self.task_manager.process_task(task)
        
        if result.success:
            video_title = result.data.title if result.data else 'N/A'
            logger.info(f"Video extracted: platform={domain}, url={params.url}, title={video_title}")
        else:
            logger.error(f"Video extraction failed: platform={domain}, url={params.url}, error={result.error}")
        
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

