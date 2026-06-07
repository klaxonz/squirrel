"""PostProcessStage - post-processing (thumbnail download, etc.)
"""
import logging

from ..base import PipelineStage
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class PostProcessStage(PipelineStage):
    """Post-processing stage

    Responsibilities:
    - Asynchronous thumbnail download
    - Other post-processing operations
    """

    def __init__(self, thumbnail_service):
        """Args:
        thumbnail_service: Thumbnail download service

        """
        self.thumbnail_service = thumbnail_service

    @property
    def stage_name(self) -> str:
        return "post_process"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute post-processing"""
        # Check if should be skipped
        if context.should_skip_post_process:
            logger.info("Skipping post-process (flag set): url=%s", context.task.url)
            return context

        video_model = context.video_model
        video_dto = context.video_dto
        # Check preconditions
        if video_model is None or video_dto is None:
            logger.warning("Missing video_model or video_dto, skipping post-process: url=%s", context.task.url)
            return context

        # 1. Asynchronously download thumbnail
        if video_dto.has_thumbnail():
            try:
                self.thumbnail_service.enqueue_download(
                    video_model.id,
                    video_dto.thumbnail,
                    video_dto.site_name,
                    source_url=context.task.url,
                )
                logger.info("Thumbnail download enqueued: video_id=%s", video_model.id)
            except (ValueError, TypeError, AttributeError) as e:
                # Thumbnail download failure should not interrupt the flow
                logger.warning("Failed to enqueue thumbnail download: video_id=%s, error=%s", video_model.id, e)

        return context

    def can_skip(self, context: PipelineContext) -> bool:
        """Skip if the skip flag is set"""
        return context.should_skip_post_process
