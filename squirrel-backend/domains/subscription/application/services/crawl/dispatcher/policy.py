from __future__ import annotations

from infrastructure.config.settings import settings


def _parse_limit_mapping(raw: str) -> dict[str, int]:
    limits: dict[str, int] = {}
    for token in (raw or "").replace(";", ",").split(","):
        token = token.strip()
        if not token or "=" not in token:
            continue
        key, value = token.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        try:
            parsed_value = int(value)
        except ValueError:
            continue
        if parsed_value < 1:
            continue
        limits[key] = parsed_value
    return limits


class CrawlDispatcherPolicy:
    def __init__(
        self,
        *,
        default_site_concurrency: int = 2,
        site_concurrency_overrides: dict[str, int] | None = None,
        task_type_limits: dict[str, int] | None = None,
    ):
        self.default_site_concurrency = max(1, default_site_concurrency)
        self.site_concurrency_overrides = site_concurrency_overrides or {}
        self.task_type_limits = task_type_limits or {}

    @classmethod
    def from_settings(cls) -> CrawlDispatcherPolicy:
        return cls(
            default_site_concurrency=settings.CRAWL_DEFAULT_SITE_CONCURRENCY,
            site_concurrency_overrides=_parse_limit_mapping(settings.CRAWL_SITE_CONCURRENCY_OVERRIDES),
            task_type_limits=_parse_limit_mapping(settings.CRAWL_TASK_TYPE_LIMITS),
        )

    def get_site_limit(self, site: str) -> int:
        return self.site_concurrency_overrides.get(site, self.default_site_concurrency)

    def get_task_type_limit(self, task_type: str) -> int | None:
        return self.task_type_limits.get(task_type)

    def is_site_available(self, site: str, running_count: int) -> bool:
        return running_count < self.get_site_limit(site)

    def is_task_type_available(self, task_type: str, running_count: int) -> bool:
        limit = self.get_task_type_limit(task_type)
        if limit is None:
            return True
        return running_count < limit
