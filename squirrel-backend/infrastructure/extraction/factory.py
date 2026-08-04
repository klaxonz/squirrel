"""Gateway-backed extractor factory."""

import logging
from urllib.parse import urlparse

from sites.crawl import SiteError
from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_registry.registry import SiteRegistry, get_site_registry

from .contracts import ExtractionResult, ExtractionTask, site_result_to_extraction_result

logger = logging.getLogger(__name__)


class SiteExtractorAdapter:
    """Adapter that exposes site integrations as the Extractor protocol."""

    def __init__(
        self,
        site_name: str,
        supported_domains: list[str],
        registry: SiteRegistry,
    ):
        self.site_name = site_name
        self.supported_domains = list(supported_domains)
        self._registry = registry

    def can_handle(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower().split(':')[0]
        except (ValueError, TypeError):
            return False
        return any(domain == item or domain.endswith(f'.{item}') for item in self.supported_domains)

    def validate_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except (ValueError, TypeError):
            return False

    def extract(self, task: ExtractionTask) -> ExtractionResult:
        try:
            result = self._registry.get_site_runtime(self.site_name).extract_video(task.url)
        except SiteError as exc:
            return ExtractionResult(
                success=False,
                error=str(exc),
                retryable=exc.retryable,
                error_context=dict(exc.context or {}),
            )

        return site_result_to_extraction_result(result)


class ExtractorFactory:
    """Resolve extractors from first-party site integrations."""

    def __init__(self, registry: SiteRegistry | None = None) -> None:
        self._instances: dict[str, SiteExtractorAdapter] = {}
        self._registry = registry or get_site_registry()

    def _create_adapter(self, site_name: str) -> SiteExtractorAdapter | None:
        if not self._registry.has_capability(site_name, 'extract_video'):
            logger.info('No extract_video capability found for site: %s', site_name)
            return None

        site_info = get_effective_site_catalog().get(site_name) or {}
        domains = list(site_info.get('domains') or [])
        if not domains:
            logger.warning('No site domains configured for extractor site: %s', site_name)
            return None

        return SiteExtractorAdapter(
            site_name=site_name,
            supported_domains=domains,
            registry=self._registry,
        )

    def create_extractor(self, url: str) -> SiteExtractorAdapter | None:
        try:
            domain = urlparse(url).netloc.lower().split(':')[0]
        except (ValueError, TypeError) as exc:
            logger.error('Failed to parse extractor URL: %s, error: %s', url, exc)
            return None

        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info('Site disabled, skip extractor creation: %s', domain)
            return None

        site_name, _ = SiteCatalog.find_site_by_domain(domain)
        if not site_name:
            logger.warning('No supported extractor site found for domain: %s', domain)
            return None

        cached = self._instances.get(site_name)
        if cached is not None:
            return cached

        adapter = self._create_adapter(site_name)
        if adapter is not None:
            self._instances[site_name] = adapter
        return adapter


_global_factory: ExtractorFactory | None = None


def get_extractor_factory() -> ExtractorFactory:
    global _global_factory
    if _global_factory is None:
        _global_factory = ExtractorFactory()
    return _global_factory


def reset_factory() -> None:
    """Reset the global factory singleton (test helper)."""
    global _global_factory
    _global_factory = None
