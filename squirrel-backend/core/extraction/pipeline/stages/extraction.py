"""
ExtractionStage - 从插件提取视频数据
"""
import logging
from typing import Optional

from crawl import Extractor
from ..base import PipelineStage
from ..context import PipelineContext
from ...exceptions import ExtractionError

logger = logging.getLogger(__name__)


class ExtractionStage(PipelineStage):
    """
    提取阶段
    
    职责：
    - 根据URL获取对应的提取器
    - 调用插件提取视频数据
    - 将结果保存到context.plugin_video
    """
    
    def __init__(self, extractor_factory):
        """
        Args:
            extractor_factory: 提取器工厂（ExtractorFactory实例）
        """
        self.extractor_factory = extractor_factory
    
    @property
    def stage_name(self) -> str:
        return "extraction"
    
    def execute(self, context: PipelineContext) -> PipelineContext:
        """执行提取"""
        # 1. 获取提取器
        extractor = self._get_extractor(context.task.url)
        
        if extractor is None:
            raise ExtractionError(
                f"No extractor found for URL: {context.task.url}",
                context={'url': context.task.url}
            )
        
        # 2. 调用插件提取
        logger.info(
            f"Extracting video: url={context.task.url}, "
            f"site={context.task.site_name}"
        )
        
        result = extractor.extract(context.task)
        
        if not result.success:
            raise ExtractionError(
                result.error or "Extraction failed",
                context={
                    'url': context.task.url,
                    'site': context.task.site_name
                }
            )
        
        # 3. 保存到上下文
        context.plugin_video = result.data
        
        logger.info(
            f"Extraction completed: url={context.task.url}, "
            f"title={getattr(result.data, 'title', 'N/A')}"
        )
        
        return context
    
    def _get_extractor(self, url: str) -> Optional[Extractor]:
        """获取提取器"""
        try:
            return self.extractor_factory.create_extractor(url)
        except Exception as e:
            logger.error(f"Failed to create extractor: {e}")
            return None
