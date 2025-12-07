"""
Pipeline工厂 - 创建配置好的Pipeline实例
"""
import logging

from .base import ExtractionPipeline
from .stages import (
    ExtractionStage,
    ValidationStage,
    PersistenceStage,
    PostProcessStage,
)
from ..adapters import PluginDataAdapter
from ..services import (
    video_persistence_service,
    actor_processor_service,
    thumbnail_downloader_service,
    download_task_creator_service,
)

logger = logging.getLogger(__name__)


class PipelineFactory:
    """
    Pipeline工厂
    
    负责创建配置好的Pipeline实例。
    """
    
    @staticmethod
    def create_video_extraction_pipeline(extractor_factory) -> ExtractionPipeline:
        """
        创建视频提取Pipeline
        
        Pipeline流程：
        1. ExtractionStage - 调用插件提取数据
        2. ValidationStage - 转换为DTO并验证
        3. PersistenceStage - 保存到数据库
        4. PostProcessStage - 后处理（缩略图、下载任务）
        
        Args:
            extractor_factory: 提取器工厂实例
            
        Returns:
            配置好的ExtractionPipeline
        """
        # 创建各个Stage
        stages = [
            # 1. 提取阶段
            ExtractionStage(extractor_factory),
            
            # 2. 验证阶段
            ValidationStage(PluginDataAdapter()),
            
            # 3. 持久化阶段
            PersistenceStage(
                video_persistence_service,
                actor_processor_service
            ),
            
            # 4. 后处理阶段
            PostProcessStage(
                thumbnail_downloader_service,
                download_task_creator_service
            ),
        ]
        
        # 创建Pipeline
        pipeline = ExtractionPipeline(stages)
        
        logger.debug(f"Created extraction pipeline with stages: {pipeline.get_stage_names()}")
        
        return pipeline


# 全局工厂实例
pipeline_factory = PipelineFactory()
