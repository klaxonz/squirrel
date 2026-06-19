"""Gateway-backed extractor factory."""

import logging
from urllib.parse import urlparse

from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_plugins.registry import SitePluginRegistry, get_site_plugin_registry

from .contracts import ExtractionResult, ExtractionTask
from .runtime_payloads import RuntimeVideoData

logger = logging.getLogger(__name__)


class SitePluginExtractorAdapter:
    """Adapter that exposes site plugin capabilities as Extractor protocol."""

    def __init__(
        self,
        site_name: str,
        supported_domains: list[str],
        plugin_registry: SitePluginRegistry,
    ):
        self.site_name = site_name
        self.supported_domains = list(supported_domains)
        self._plugin_registry = plugin_registry

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
        response = self._plugin_registry.invoke(
            'extract_video',
            site_name=self.site_name,
            payload={
                'url': task.url,
                'site_name': task.site_name,
                'task_id': task.task_id,
                'retry_count': task.retry_count,
                'max_retries': task.max_retries,
                'metadata': dict(task.metadata or {}),
            },
        )
        if not response.ok:
            message = response.error.message if response.error else f'Extraction failed for site: {self.site_name}'
            return ExtractionResult(
                success=False,
                error=message,
                retryable=response.error.retryable if response.error else False,
                error_context=response.error.details if response.error else None,
            )

        payload = response.data
        if isinstance(payload, dict) and 'success' in payload:
            return ExtractionResult.from_dict(payload)
        if isinstance(payload, dict):
            return ExtractionResult.success_result(RuntimeVideoData.from_dict(payload))
        return ExtractionResult(success=False, error='Plugin extract_video returned an invalid payload')


class ExtractorFactory:
    """Resolve extractors from first-party site plugins."""

    def __init__(self, plugin_registry: SitePluginRegistry | None = None) -> None:
        self._instances: dict[str, SitePluginExtractorAdapter] = {}
        self._plugin_registry = plugin_registry or get_site_plugin_registry()

    def _create_adapter(self, site_name: str) -> SitePluginExtractorAdapter | None:
        if not self._plugin_registry.has_capability(site_name, 'extract_video'):
            logger.info('No extract_video capability found for site: %s', site_name)
            return None

        site_info = get_effective_site_catalog().get(site_name) or {}
        domains = list(site_info.get('domains') or [])
        if not domains:
            logger.warning('No site domains configured for extractor site: %s', site_name)
            return None

        return SitePluginExtractorAdapter(
            site_name=site_name,
            supported_domains=domains,
            plugin_registry=self._plugin_registry,
        )

    def create_extractor(self, url: str) -> SitePluginExtractorAdapter | None:
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
