"""Video extraction result handler (refactored - uses Pipeline)

Refactoring improvements:
1. Simplified responsibilities: only handles Pipeline coordination
2. Uses Pipeline for the entire workflow
3. Code reduced from 270 lines to < 100 lines
"""
import logging

from ..base import BaseResultHandler
from ..contracts import ExtractionResult, ExtractionTask
from ..factory import get_extractor_factory
from ..pipeline import PipelineContext
from ..pipeline.factory import pipeline_factory

logger = logging.getLogger(__name__)


class VideoExtractionHandler(BaseResultHandler):
    """Video extraction result handler (refactored)

    Responsibilities:
    - Create Pipeline context
    - Execute Pipeline
    - Handle Pipeline results

    Note: Actual business logic lives in the Pipeline Stages.
    """

    def __init__(self, pipeline=None):
        """Initialize the handler

        Args:
            pipeline: Pipeline instance (optional, for test injection)

        """
        if pipeline is None:
            # Create default Pipeline via factory
            extractor_factory = get_extractor_factory()
            pipeline = pipeline_factory.create_video_extraction_pipeline(
                extractor_factory,
            )

        self.pipeline = pipeline

    def handle_failure(
        self,
        task: ExtractionTask,
        result: ExtractionResult,
    ) -> None:
        """Handle failed result

        Args:
            task: Extraction task
            result: Extraction result

        """
        logger.error("Video extraction failed: task_id=%s, url=%s, error=%s", task.task_id, task.url, result.error)

    def process(self, task: ExtractionTask) -> ExtractionResult:
        """Process extraction task (new method)

        This is the new entry point, using Pipeline directly.

        Args:
            task: Extraction task

        Returns:
            ExtractionResult

        """
        try:
            # 1. Create Pipeline context
            context = self._create_context(task)

            # 2. Execute Pipeline
            logger.info("Processing extraction task: task_id=%s, url=%s", task.task_id, task.url)

            pipeline_result = self.pipeline.execute(context)

            # 3. Log result
            if pipeline_result.success:
                logger.info("Extraction completed successfully: task_id=%s, duration=%f'.2f's", task.task_id, context.get_duration())
            else:
                logger.error("Extraction failed: task_id=%s, error=%s", task.task_id, pipeline_result.error)

            return pipeline_result

        except Exception as e:  # handler boundary — catch all to return ExtractionResult
            logger.error("Unexpected error in VideoExtractionHandler: task_id=%s, error=%s", task.task_id, e, exc_info=True)

            return ExtractionResult(
                success=False,
                error=str(e),
            )

    def _create_context(self, task: ExtractionTask) -> PipelineContext:
        """Create Pipeline context

        Args:
            task: Extraction task

        Returns:
            PipelineContext

        """
        context = PipelineContext(task=task)

        # Set control flags based on task metadata
        context.should_skip_post_process = bool(task.metadata.get("skip_post_process", False))

        # Skip persistence if subscription does not exist
        # (This check can be performed in PersistenceStage)

        return context


# Singleton instance (uses default Pipeline)
video_extraction_handler = VideoExtractionHandler()
