"""Pipeline工厂 - 创建配置好的Pipeline实例
"""
import logging

from ..adapters import RuntimeDataAdapter
from ..services import (
    actor_processor_service,
    thumbnail_downloader_service,
    video_persistence_service,
)
from .base import ExtractionPipeline, PipelineStage
from .config import PipelineConfig, StageConfig
from .stages import (
    ExtractionStage,
    PersistenceStage,
    PostProcessStage,
    ValidationStage,
)

logger = logging.getLogger(__name__)


class PipelineFactory:
    """Pipeline工厂

    负责创建配置好的Pipeline实例。
    """

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig.default()
        self._stage_builders = {
            ExtractionStage: self._build_extraction_stage,
            ValidationStage: self._build_validation_stage,
            PersistenceStage: self._build_persistence_stage,
            PostProcessStage: self._build_post_process_stage,
        }

    def _build_extraction_stage(self, stage_config: StageConfig, extractor_factory) -> PipelineStage:
        return ExtractionStage(extractor_factory)

    def _build_validation_stage(self, stage_config: StageConfig, extractor_factory) -> PipelineStage:
        return ValidationStage(RuntimeDataAdapter())

    def _build_persistence_stage(self, stage_config: StageConfig, extractor_factory) -> PipelineStage:
        return PersistenceStage(
            video_persistence_service,
            actor_processor_service,
        )

    def _build_post_process_stage(self, stage_config: StageConfig, extractor_factory) -> PipelineStage:
        return PostProcessStage(thumbnail_downloader_service)

    def _build_stage(self, stage_config: StageConfig, extractor_factory) -> PipelineStage | None:
        builder = self._stage_builders.get(stage_config.stage_class)
        if builder:
            return builder(stage_config, extractor_factory)
        if stage_config.params:
            return stage_config.stage_class(**stage_config.params)
        return stage_config.stage_class()

    def create_pipeline(self, extractor_factory) -> ExtractionPipeline:
        stages = []
        for stage_config in self.config.get_enabled_stages():
            stage = self._build_stage(stage_config, extractor_factory)
            if stage:
                stages.append(stage)
        pipeline = ExtractionPipeline(stages)
        logger.debug("Created pipeline with stages: %s", pipeline.get_stage_names())
        return pipeline

    @staticmethod
    def create_video_extraction_pipeline(extractor_factory) -> ExtractionPipeline:
        """创建视频提取Pipeline（向后兼容的静态方法）

        Args:
            extractor_factory: 提取器工厂实例

        Returns:
            配置好的ExtractionPipeline

        """
        factory = PipelineFactory()
        return factory.create_pipeline(extractor_factory)


pipeline_factory = PipelineFactory()
