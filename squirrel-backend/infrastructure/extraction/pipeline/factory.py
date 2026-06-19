"""Video extraction pipeline assembly.

One fixed pipeline: extraction -> validation -> persistence -> post-process.
Stages are wired with their concrete services; there is no configurable
stage list (the old PipelineConfig/StageConfig indirection was removed — only
one caller, one pipeline, no disabled/parametrized stages ever existed).
"""

import logging

from domains.video.application.services.extraction.actor_processor import actor_processor_service
from domains.video.application.services.extraction.thumbnail_downloader import thumbnail_downloader_service
from domains.video.application.services.extraction.video_persistence import video_persistence_service

from ..adapters.runtime_adapter import RuntimeDataAdapter
from .base import ExtractionPipeline
from .stages.extraction import ExtractionStage
from .stages.persistence import PersistenceStage
from .stages.post_process import PostProcessStage
from .stages.validation import ValidationStage

logger = logging.getLogger(__name__)


def create_video_extraction_pipeline(extractor_factory) -> ExtractionPipeline:
    """Build the video-extraction pipeline with its default stages in order.

    Args:
        extractor_factory: ExtractorFactory used by ExtractionStage.

    Returns:
        ExtractionPipeline ready to ``execute(context)``.

    """
    pipeline = ExtractionPipeline(
        [
            ExtractionStage(extractor_factory),
            ValidationStage(RuntimeDataAdapter()),
            PersistenceStage(video_persistence_service, actor_processor_service),
            PostProcessStage(thumbnail_downloader_service),
        ]
    )
    logger.debug('Created pipeline with stages: %s', pipeline.get_stage_names())
    return pipeline
