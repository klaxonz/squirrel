class CrawlTaskError(Exception):
    """Base crawl task service error."""


class CrawlTaskOwnershipError(CrawlTaskError):
    """Raised when the worker does not own the task lease."""


class CrawlTaskNotFoundError(CrawlTaskError):
    """Raised when the target task does not exist."""


class CrawlTaskStateError(CrawlTaskError):
    """Raised when the target task is not in a valid state for the operation."""
