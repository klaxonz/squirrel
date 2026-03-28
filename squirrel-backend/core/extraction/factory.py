"""
Gateway-backed extractor factory.
"""
import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse

from crawl import ExtractionResult, ExtractionTask, VideoMeta

from plugins.manager import get_plugin_manager
from utils.site_catalog import SiteCatalog

logger = logging.getLogger(__name__)


class GatewayExtractorAdapter:
    """Adapter that exposes plugin runtime capabilities as Extractor protocol."""

    def __init__(self, site_name: str, supported_domains: List[str]):
        self.site_name = site_name
        self.supported_domains = list(supported_domains)

    def can_handle(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower().split(':')[0]
        except Exception:
            return False
        return any(domain == item or domain.endswith(f'.{item}') for item in self.supported_domains)

    def validate_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except Exception:
            return False

    def extract(self, task: ExtractionTask) -> ExtractionResult:
        response = get_plugin_manager().gateway.invoke(
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
            return ExtractionResult.success_result(VideoMeta.from_dict(payload))
        return ExtractionResult(success=False, error='Plugin extract_video returned an invalid payload')


class ExtractorFactory:
    """Resolve extractors from plugin runtime registrations."""

    def __init__(self):
        self._instances: Dict[str, GatewayExtractorAdapter] = {}

    def _create_adapter(self, site_name: str) -> Optional[GatewayExtractorAdapter]:
        route = get_plugin_manager().gateway.resolve_route('extract_video', site_name=site_name)
        if route is None:
            logger.info(f'No extract_video capability found for site: {site_name}')
            return None

        site_info = SiteCatalog.get_catalog().get(site_name) or {}
        domains = list(site_info.get('domains') or [])
        if not domains:
            logger.warning(f'No site domains configured for extractor site: {site_name}')
            return None

        return GatewayExtractorAdapter(site_name=site_name, supported_domains=domains)

    def create_extractor(self, url: str) -> Optional[GatewayExtractorAdapter]:
        try:
            domain = urlparse(url).netloc.lower().split(':')[0]
        except Exception as exc:
            logger.error(f'Failed to parse extractor URL: {url}, error: {exc}')
            return None

        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info(f'Site disabled, skip extractor creation: {domain}')
            return None

        site_name, _ = SiteCatalog.find_site_by_domain(domain)
        if not site_name:
            logger.warning(f'No supported extractor site found for domain: {domain}')
            return None

        cached = self._instances.get(site_name)
        if cached is not None:
            return cached

        adapter = self._create_adapter(site_name)
        if adapter is not None:
            self._instances[site_name] = adapter
        return adapter

    def get_extractor_by_site(self, site_name: str) -> Optional[GatewayExtractorAdapter]:
        if not SiteCatalog.is_site_enabled(site=site_name):
            logger.info(f'Site disabled, skip extractor lookup: {site_name}')
            return None

        cached = self._instances.get(site_name)
        if cached is not None:
            return cached

        adapter = self._create_adapter(site_name)
        if adapter is not None:
            self._instances[site_name] = adapter
        return adapter

    def clear_cache(self) -> None:
        self._instances.clear()

    def register(self, site_name: str, extractor_class, domains: List[str]) -> None:
        logger.info(f'Ignoring legacy extractor registration for site: {site_name}, domains: {domains}')

    def get_test_url(self, site_name: str) -> Optional[str]:
        site_info = SiteCatalog.get_catalog().get(site_name) or {}
        return site_info.get('test_url')

    def get_all_sites(self) -> List[str]:
        return list(SiteCatalog.get_catalog().keys())

    def get_all_domains(self) -> List[str]:
        return SiteCatalog.get_all_domains()


_global_factory: Optional[ExtractorFactory] = None


def get_extractor_factory() -> ExtractorFactory:
    global _global_factory
    if _global_factory is None:
        _global_factory = ExtractorFactory()
    return _global_factory


def reset_factory() -> None:
    global _global_factory
    if _global_factory is not None:
        _global_factory.clear_cache()
    _global_factory = None
