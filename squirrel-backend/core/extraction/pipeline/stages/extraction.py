"""ExtractionStage - extracts video data from plugin
"""
import logging

from services.blocked_video_service import record_blocked_video

from ...contracts import Extractor
from ...exceptions import (
    ExtractionError,
    NetworkError,
    PermissionError,
    ResourceNotFoundError,
    VipError,
)
from ..base import PipelineStage
from ..context import PipelineContext

logger = logging.getLogger(__name__)


class ExtractionStage(PipelineStage):
    """Extraction stage

    Responsibilities:
    - Get the appropriate extractor for the URL
    - Invoke the plugin to extract video data
    - Save the result to context.plugin_video
    """

    def __init__(self, extractor_factory):
        """Args:
        extractor_factory: Extractor factory (ExtractorFactory instance)

        """
        self.extractor_factory = extractor_factory

    @property
    def stage_name(self) -> str:
        return "extraction"

    def execute(self, context: PipelineContext) -> PipelineContext:
        """Execute extraction"""
        extractor = self._get_extractor(context.task.url)

        if extractor is None:
            raise ExtractionError(
                f"No extractor found for URL: {context.task.url}",
                context={"url": context.task.url},
            )

        logger.info("Extracting video: url=%s, site=%s", context.task.url, context.task.site_name)

        result = extractor.extract(context.task)

        if not result.success:
            error_context = {
                "url": context.task.url,
                "site": context.task.site_name,
                "error_category": result.error_category,
                "retryable": result.retryable,
                **(result.error_context or {}),
            }

            error_msg = result.error or "Extraction failed"

            if result.error_category == "network":
                raise NetworkError(error_msg, context=error_context)
            if result.error_category == "auth":
                raise PermissionError(error_msg, context=error_context)
            if result.error_category == "vip":
                raise VipError(error_msg, context=error_context)
            if result.error_category == "not_found":
                raise ResourceNotFoundError(error_msg, context=error_context)
            raise ExtractionError(
                error_msg,
                retryable=result.retryable,
                context=error_context,
            )

        context.plugin_video = result.data

        logger.info("Extraction completed: url=%s, title=%s", context.task.url, getattr(result.data, 'title', 'N/A'))

        return context

    def on_error(self, context: PipelineContext, error: Exception) -> None:
        """Error handling callback"""
        # Call parent error handling
        super().on_error(context, error)

        reason_code = None
        if isinstance(error, VipError):
            reason_code = "vip_required"
        elif isinstance(getattr(error, "context", None), dict):
            reason_code = error.context.get("blocked_reason_code")

        if not reason_code:
            return

        try:
            record_blocked_video(
                url=context.task.url,
                reason_code=reason_code,
                error_message=str(error),
                error_type=type(error).__name__,
            )
        except (ConnectionError, OSError, ValueError, TypeError) as record_error:
            logger.warning("Failed to record blocked video: %s", record_error)

    def _get_extractor(self, url: str) -> Extractor | None:
        """Get extractor for URL"""
        try:
            return self.extractor_factory.create_extractor(url)
        except (ValueError, TypeError, AttributeError) as e:
            logger.error("Failed to create extractor: %s", e)
            return None
