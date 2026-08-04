class SubscriptionUpdateError(Exception):
    """Classified site-integration failure that survives the orchestrator boundary."""

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
        try:
            self.retry_after_seconds = max(0, int(retry_after_seconds)) if retry_after_seconds is not None else None
        except (TypeError, ValueError):
            self.retry_after_seconds = None
