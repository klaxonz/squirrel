"""Base extraction implementations.
"""
import logging

from .contracts import ExtractionResult, ExtractionTask

logger = logging.getLogger(__name__)


class BaseResultHandler:
    """Base result handler."""

    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """Handle successful extraction results."""
        logger.info("Task succeeded: %s", task.task_id)

    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """Handle failed extraction results."""
        logger.error("Task failed: %s, error: %s", task.task_id, result.error)
