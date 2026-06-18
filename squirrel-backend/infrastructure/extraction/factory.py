"""Gateway-backed extractor factory.
"""
import logging
from urllib.parse import urlparse

from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.catalog import SiteCatalog
from infrastructure.site_runtimes.gateway import SiteRuntimeGateway
from infrastructure.site_runtimes.runtime_provider import get_runtime_gateway

from .contracts import ExtractionResult, ExtractionTask
from .runtime_payloads import RuntimeVideoData

logger = logging.getLogger(__name__)


class GatewayExtractorAdapter:
    """Adapter that exposes site runtime capabilities as Extractor protocol."""

    def __init__(
        self,
        site_name: str,
        supported_domains: list[str],
        runtime_gateway: SiteRuntimeGateway,
    ):
        self.site_name = site_name
        self.supported_domains = list(supported_domains)
        self._runtime_gateway = runtime_gateway

    def can_handle(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower().split(":")[0]
        except (ValueError, TypeError):
            return False
        return any(domain == item or domain.endswith(f".{item}") for item in self.supported_domains)

    def validate_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return bool(parsed.scheme and parsed.netloc)
        except (ValueError, TypeError):
            return False

    def extract(self, task: ExtractionTask) -> ExtractionResult:
        response = self._runtime_gateway.invoke(
            "extract_video",
            site_name=self.site_name,
            payload={
                "url": task.url,
                "site_name": task.site_name,
                "task_id": task.task_id,
                "retry_count": task.retry_count,
                "max_retries": task.max_retries,
                "metadata": dict(task.metadata or {}),
            },
        )
        if not response.ok:
            message = response.error.message if response.error else f"Extraction failed for site: {self.site_name}"
            return ExtractionResult(
                success=False,
                error=message,
                retryable=response.error.retryable if response.error else False,
                error_context=response.error.details if response.error else None,
            )

        payload = response.data
        if isinstance(payload, dict) and "success" in payload:
            return ExtractionResult.from_dict(payload)
        if isinstance(payload, dict):
            return ExtractionResult.success_result(RuntimeVideoData.from_dict(payload))
        return ExtractionResult(success=False, error="Plugin extract_video returned an invalid payload")


class ExtractorFactory:
    """Resolve extractors from site runtime registrations."""

    def __init__(self, runtime_gateway: SiteRuntimeGateway | None = None) -> None:
        self._instances: dict[str, GatewayExtractorAdapter] = {}
        # Allow either explicit injection (preferred — tests pass a fake) or
        # lazy resolution from the runtime provider (production module singleton).
        self._runtime_gateway = runtime_gateway

    def _resolve_gateway(self) -> SiteRuntimeGateway:
        return self._runtime_gateway or get_runtime_gateway()

    def _create_adapter(self, site_name: str) -> GatewayExtractorAdapter | None:
        runtime_gateway = self._resolve_gateway()
        route = runtime_gateway.resolve_route("extract_video", site_name=site_name)
        if route is None:
            logger.info("No extract_video capability found for site: %s", site_name)
            return None

        site_info = get_effective_site_catalog().get(site_name) or {}
        domains = list(site_info.get("domains") or [])
        if not domains:
            logger.warning("No site domains configured for extractor site: %s", site_name)
            return None

        return GatewayExtractorAdapter(
            site_name=site_name,
            supported_domains=domains,
            runtime_gateway=runtime_gateway,
        )

    def create_extractor(self, url: str) -> GatewayExtractorAdapter | None:
        try:
            domain = urlparse(url).netloc.lower().split(":")[0]
        except (ValueError, TypeError) as exc:
            logger.error("Failed to parse extractor URL: %s, error: %s", url, exc)
            return None

        if not SiteCatalog.is_site_enabled(domain=domain):
            logger.info("Site disabled, skip extractor creation: %s", domain)
            return None

        site_name, _ = SiteCatalog.find_site_by_domain(domain)
        if not site_name:
            logger.warning("No supported extractor site found for domain: %s", domain)
            return None

        cached = self._instances.get(site_name)
        if cached is not None:
            return cached

        adapter = self._create_adapter(site_name)
        if adapter is not None:
            self._instances[site_name] = adapter
        return adapter

    def get_extractor_by_site(self, site_name: str) -> GatewayExtractorAdapter | None:
        if not SiteCatalog.is_site_enabled(site=site_name):
            logger.info("Site disabled, skip extractor lookup: %s", site_name)
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

    def get_test_url(self, site_name: str) -> str | None:
        site_info = get_effective_site_catalog().get(site_name) or {}
        return site_info.get("test_url")

    def get_all_sites(self) -> list[str]:
        return list(get_effective_site_catalog().keys())

    def get_all_domains(self) -> list[str]:
        return SiteCatalog.get_all_domains()


_global_factory: ExtractorFactory | None = None


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


