class SubscriptionImportError(Exception):
    """Classified importer failure consumed by the durable task retry policy."""

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
        self.error_type = error_type or 'subscription_import_failed'
        try:
            self.retry_after_seconds = (
                max(0, int(retry_after_seconds)) if retry_after_seconds is not None else None
            )
        except (TypeError, ValueError):
            self.retry_after_seconds = None
