"""Base extraction implementations.
"""
import logging
from urllib.parse import urlparse

from .contracts import ExtractionResult, ExtractionTask, Extractor, ResultHandler

logger = logging.getLogger(__name__)


class BaseExtractor:
    """Base extractor implementation."""

    def __init__(self, site_name: str, supported_domains: list[str]):
        self.site_name = site_name
        self._supported_domains = supported_domains

    @property
    def supported_sites(self) -> list[str]:
        return [self.site_name]

    def can_handle(self, url: str) -> bool:
        """Check if the extractor can handle the given URL."""
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            for supported_domain in self._supported_domains:
                if domain == supported_domain or domain.endswith(f".{supported_domain}"):
                    return True
            return False
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse URL: %s, error: %s", url, e)
            return False

    def validate_url(self, url: str) -> bool:
        """Validate URL format."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc])
        except (ValueError, TypeError):
            return False

    def extract(self, task: ExtractionTask) -> ExtractionResult:
        """Base extraction implementation; subclasses should override."""
        if not self.can_handle(task.url):
            return ExtractionResult(
                success=False,
                error=f"Unsupported URL: {task.url}",
            )

        if not self.validate_url(task.url):
            return ExtractionResult(
                success=False,
                error=f"Invalid URL format: {task.url}",
            )

        return self._do_extract(task)

    def _do_extract(self, task: ExtractionTask) -> ExtractionResult:
        """Concrete extraction logic; must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement _do_extract.")


class BaseTaskProcessor:
    """Base task processor."""

    def __init__(self, extractor: Extractor, result_handler: ResultHandler):
        self.extractor = extractor
        self.result_handler = result_handler

    def can_process(self, task: ExtractionTask) -> bool:
        """Check whether the task can be processed."""
        extractor = self._get_extractor_for_task(task)
        return extractor.can_handle(task.url) if extractor else False

    def process(self, task: ExtractionTask) -> ExtractionResult:
        """Process the given task."""
        extractor = self._get_extractor_for_task(task)
        if extractor is None:
            raise ValueError("No available extractor found.")
        return self._process_with_extractor(extractor, task)

    def _get_extractor_for_task(self, task: ExtractionTask) -> Extractor | None:
        """Return the extractor to use for the task; defaults to the provided extractor."""
        return self.extractor

    def _process_with_extractor(self, extractor: Extractor, task: ExtractionTask) -> ExtractionResult:
        """Process the task with the specified extractor."""
        if extractor is None:
            raise ValueError("Extractor not configured.")

        try:
            logger.info("Start execute extract task, task_id: %s, url: %s", task.task_id, task.url)

            result = extractor.extract(task)

            if result.success:
                self.result_handler.handle_success(task, result)
                title = result.data.title if result.data else "unknown"
                logger.info("Task processed successfully: %s, title: %s", task.task_id, title)
            else:
                self.result_handler.handle_failure(task, result)
                logger.error("Task processing failed: %s, error: %s", task.task_id, result.error)

            return result

        except (ValueError, TypeError, AttributeError) as e:
            error_msg = f"Task processing exception: {task.task_id}, error: {e!s}"
            logger.error(error_msg, exc_info=True)

            result = ExtractionResult(
                success=False,
                error=error_msg,
            )

            self.result_handler.handle_failure(task, result)
            return result


class BaseResultHandler:
    """Base result handler."""

    def handle_success(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """Handle successful extraction results."""
        logger.info("Task succeeded: %s", task.task_id)

    def handle_failure(self, task: ExtractionTask, result: ExtractionResult) -> None:
        """Handle failed extraction results."""
        logger.error("Task failed: %s, error: %s", task.task_id, result.error)
