"""ValidationStage - validates and converts data to DTO"""

import logging

from ...adapters.runtime_adapter import RuntimeDataAdapter
from ...exceptions import ValidationError as ExtValidationError
from ..base import PipelineStage
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class ValidationStage(PipelineStage):
    """Validation stage

    Responsibilities:
    - Convert site Video object to VideoDTO
    - Validate data integrity and format
    - Save to context.video_dto
    """

    def __init__(self, adapter: RuntimeDataAdapter):
        """Args:
        adapter: Site data adapter

        """
        self.adapter = adapter

    @property
    def stage_name(self) -> str:
        return 'validation'

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute validation and conversion"""
        # Check preconditions
        if context.site_video is None:
            raise ExtValidationError(
                'No site video data found in context',
                context={'task_id': context.task.task_id},
            )

        # Convert to DTO (automatically validates)
        logger.info('Validating video data: url=%s', context.task.url)

        video_dto = self.adapter.adapt(
            context.site_video,
            context.task.site_name,
        )

        # Save to context
        context.video_dto = video_dto

        logger.info(
            'Validation completed: url=%s, title=%s, actors=%s',
            context.task.url,
            video_dto.title,
            len(video_dto.actors),
        )

        return context

    def can_skip(self, context: PipelineContext) -> bool:
        """Skip if video_dto already exists"""
        return context.video_dto is not None
