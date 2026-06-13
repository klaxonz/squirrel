"""Pipeline base class definitions
"""
import logging
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional

from ..contracts import ExtractionResult
from ..exceptions import StageExecutionError
from .context import PipelineContext

if TYPE_CHECKING:
    from .middleware import MiddlewareChain

logger = logging.getLogger(__name__)


class PipelineStage(ABC):
    """Pipeline stage base class

    Each Stage handles a specific step in the Pipeline.
    """

    @property
    @abstractmethod
    def stage_name(self) -> str:
        """Stage name (for logging and error tracing)"""

    @abstractmethod
    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute stage logic

        Args:
            context: Pipeline context

        Returns:
            Updated context

        Raises:
            StageExecutionError: Stage execution failed

        """

    def can_skip(self, context: PipelineContext) -> bool:
        """Check whether this stage can be skipped

        Args:
            context: Pipeline context

        Returns:
            True to skip, False to execute

        """
        return False

    def on_error(self, context: PipelineContext, error: Exception) -> None:
        """Error handling callback

        Args:
            context: Pipeline context
            error: Caught exception

        """
        error_msg = f"Stage '{self.stage_name}' failed: {error!s}"

        logger.error(
            error_msg,
            exc_info=True,
            extra={
                "task_id": context.task.task_id,
                "url": context.task.url,
                "stage": self.stage_name,
                "error_type": type(error).__name__,
            },
        )

        context.add_error(self.stage_name, str(error))


class ExtractionPipeline:
    """Extraction pipeline

    Executes multiple Stages in sequence to complete the full extraction flow.
    """

    def __init__(self, stages: list[PipelineStage], middleware: Optional["MiddlewareChain"] = None):
        """Initialize the pipeline

        Args:
            stages: List of Stages (in execution order)
            middleware: Middleware chain (optional)

        """
        self.stages = stages
        self._middleware = middleware
        self.logger = logger

    def execute(self, context: PipelineContext) -> ExtractionResult:
        """Execute the pipeline

        Args:
            context: Pipeline context

        Returns:
            ExtractionResult

        """
        try:
            self.logger.info("Pipeline started: task_id=%s, url=%s", context.task.task_id, context.task.url)

            # Execute Stages in sequence
            for stage in self.stages:
                context.current_stage = stage.stage_name

                # Check if this stage can be skipped
                if stage.can_skip(context):
                    self.logger.debug("Skipping stage '%s': task_id=%s", stage.stage_name, context.task.task_id)
                    continue

                # Execute Stage
                try:
                    self.logger.debug("Executing stage '%s': task_id=%s", stage.stage_name, context.task.task_id)

                    if self._middleware:
                        self._middleware.before_stage(context, stage)

                    context = stage.execute(context)

                    if self._middleware:
                        self._middleware.after_stage(context, stage)

                    self.logger.debug("Stage '%s' completed: task_id=%s", stage.stage_name, context.task.task_id)

                except (ValueError, TypeError, AttributeError, KeyError) as e:
                    # Stage execution failed
                    stage.on_error(context, e)
                    if self._middleware:
                        self._middleware.on_error(context, stage, e)

                    # Determine whether to continue
                    if not self._should_continue_after_error(stage, e):
                        raise StageExecutionError(
                            f"Critical stage '{stage.stage_name}' failed",
                            stage_name=stage.stage_name,
                            context={
                                "task_id": context.task.task_id,
                                "url": context.task.url,
                                "error": str(e),
                            },
                        ) from e

            # All Stages completed
            duration = context.get_duration()

            self.logger.info("Pipeline completed successfully: task_id=%s, duration=%f'.2f's", context.task.task_id, duration)

            return ExtractionResult(
                success=True,
                data=context.video_dto,
            )

        except Exception as e:  # pipeline execution boundary — catch all to return ExtractionResult
            import traceback
            duration = context.get_duration()

            self.logger.error("Pipeline failed: task_id=%s, duration=%f'.2f's, error=%s", context.task.task_id, duration, e, exc_info=True)

            # Record detailed error info (with stack trace) to metrics
            try:
                from services.observability.collector.instance import metrics
                from utils.url_helper import extract_top_level_domain
                stack_trace = traceback.format_exc()
                site = extract_top_level_domain(context.task.url) if context.task.url else "unknown"
                metrics.record_error(
                    site=site,
                    url=context.task.url,
                    error_type=type(e).__name__,
                    error_msg=f"{e!s}\n\n{stack_trace}",
                )
            except Exception:  # metrics recording must never fail
                pass

            return ExtractionResult(
                success=False,
                error=str(e),
            )

    def _should_continue_after_error(
        self,
        stage: PipelineStage,
        error: Exception,
    ) -> bool:
        """Determine whether to continue after a stage failure

        Args:
            stage: The failed Stage
            error: Caught exception

        Returns:
            True to continue, False to abort

        """
        # Define critical stages (failure must abort)
        critical_stages = {
            "extraction",      # Extraction failed, cannot continue
            "validation",      # Validation failed, data is incomplete
            "persistence",     # Persistence failed, cannot save
        }

        # Critical stage failure must abort
        if stage.stage_name in critical_stages:
            return False

        # Non-critical stage failure can continue (e.g. enrichment, post_process)
        return True

    def get_stage_names(self) -> list[str]:
        """Get all stage names"""
        return [stage.stage_name for stage in self.stages]

    def __repr__(self):
        stage_names = ", ".join(self.get_stage_names())
        return f"ExtractionPipeline(stages=[{stage_names}])"
