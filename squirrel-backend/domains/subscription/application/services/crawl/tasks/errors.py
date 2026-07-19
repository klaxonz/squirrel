class CrawlTaskError(Exception):
    """Base crawl task service error."""


class CrawlTaskOwnershipError(CrawlTaskError):
    """Raised when the worker does not own the task lease."""


class CrawlTaskNotFoundError(CrawlTaskError):
    """Raised when the target task does not exist."""


class CrawlTaskStateError(CrawlTaskError):
    """Raised when the target task is not in a valid state for the operation."""

    retryable = False
    error_type = 'crawl_task_state'


class CrawlExecutionError(CrawlTaskError):
    """Structured execution failure used by the durable task retry policy."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool,
        error_type: str | None = None,
        retry_after_seconds: int | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.error_type = error_type
        self.retry_after_seconds = retry_after_seconds
