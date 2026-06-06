"""
视频提取结果处理器（重构版 - 使用Pipeline）

重构改进：
1. 职责精简：只负责Pipeline的协调
2. 使用Pipeline处理整个流程
3. 代码从270行缩减到 < 100行
"""
import logging

from ..base import BaseResultHandler
from ..contracts import ExtractionResult, ExtractionTask
from ..pipeline import PipelineContext
from ..pipeline.factory import pipeline_factory
from ..factory import get_extractor_factory

logger = logging.getLogger(__name__)


class VideoExtractionHandler(BaseResultHandler):
    """
    视频提取结果处理器（重构版）
    
    职责：
    - 创建Pipeline上下文
    - 执行Pipeline
    - 处理Pipeline结果
    
    注意：实际的业务逻辑都在Pipeline的各个Stage中。
    """
    
    def __init__(self, pipeline=None):
        """
        初始化Handler
        
        Args:
            pipeline: Pipeline实例（可选，用于测试注入）
        """
        if pipeline is None:
            # 使用工厂创建默认Pipeline
            extractor_factory = get_extractor_factory()
            pipeline = pipeline_factory.create_video_extraction_pipeline(
                extractor_factory
            )
        
        self.pipeline = pipeline
    
    def handle_failure(
        self,
        task: ExtractionTask,
        result: ExtractionResult
    ) -> None:
        """
        处理失败结果
        
        Args:
            task: 提取任务
            result: 提取结果
        """
        logger.error(
            f"Video extraction failed: task_id={task.task_id}, "
            f"url={task.url}, error={result.error}"
        )
    
    def process(self, task: ExtractionTask) -> ExtractionResult:
        """
        处理提取任务（新方法）
        
        这是新的入口方法，直接使用Pipeline处理。
        
        Args:
            task: 提取任务
            
        Returns:
            ExtractionResult
        """
        try:
            # 1. 创建Pipeline上下文
            context = self._create_context(task)
            
            # 2. 执行Pipeline
            logger.info(
                f"Processing extraction task: task_id={task.task_id}, "
                f"url={task.url}"
            )
            
            result = self.pipeline.execute(context)
            
            # 3. 记录结果
            if result.success:
                logger.info(
                    f"Extraction completed successfully: task_id={task.task_id}, "
                    f"duration={context.get_duration():.2f}s"
                )
            else:
                logger.error(
                    f"Extraction failed: task_id={task.task_id}, "
                    f"error={result.error}"
                )
            
            return result
        
        except Exception as e:  # handler boundary — catch all to return ExtractionResult
            logger.error(
                f"Unexpected error in VideoExtractionHandler: "
                f"task_id={task.task_id}, error={e}",
                exc_info=True
            )
            
            return ExtractionResult(
                success=False,
                error=str(e)
            )
    
    def _create_context(self, task: ExtractionTask) -> PipelineContext:
        """
        创建Pipeline上下文
        
        Args:
            task: 提取任务
            
        Returns:
            PipelineContext
        """
        context = PipelineContext(task=task)

        # 根据任务元数据设置控制标志
        context.should_skip_post_process = bool(task.metadata.get('skip_post_process', False))

        # 如果订阅不存在，跳过持久化
        # （这个检查可以在PersistenceStage中进行）

        return context


# 单例实例（使用默认Pipeline）
video_extraction_handler = VideoExtractionHandler()
