"""Extractor plugin registry for Squirrel Crawl SDK."""
from __future__ import annotations

from threading import RLock
from typing import Dict, List, Optional, Type

from .interfaces import IExtractor


class ExtractorRegistry:
    """Keep track of registered extractor classes by site name."""

    def __init__(self) -> None:
        self._extractors: Dict[str, Type[IExtractor]] = {}
        self._domain_mapping: Dict[str, str] = {}
        self._lock = RLock()

    def register(self, site_name: str, extractor_class: Type[IExtractor], domains: List[str]) -> None:
        with self._lock:
            if site_name in self._extractors:
                raise ValueError(f"Extractor already registered for site: {site_name}")

            # Validate extractor metadata
            if not getattr(extractor_class, "site_name", None):
                extractor_class.site_name = site_name  # type: ignore[attr-defined]
            if not getattr(extractor_class, "supported_domains", None):
                extractor_class.supported_domains = domains  # type: ignore[attr-defined]

            self._extractors[site_name] = extractor_class
            for d in domains:
                self._domain_mapping[d] = site_name

    def get_extractor_class(self, site_name: str) -> Optional[Type[IExtractor]]:
        return self._extractors.get(site_name)

    def get_site_by_domain(self, domain: str) -> Optional[str]:
        return self._domain_mapping.get(domain)

    def get_all_sites(self) -> List[str]:
        return list(self._extractors.keys())

    def get_all_domains(self) -> List[str]:
        return list(self._domain_mapping.keys())


_registry_singleton: Optional[ExtractorRegistry] = None


def get_extractor_registry() -> ExtractorRegistry:
    global _registry_singleton
    if _registry_singleton is None:
        _registry_singleton = ExtractorRegistry()
    return _registry_singleton


class ExtractorFactory:
    """Create and cache extractor instances based on URL or site name."""

    def __init__(self, registry: ExtractorRegistry):
        self.registry = registry
        self._instances: Dict[str, IExtractor] = {}

    def create_extractor(self, url: str) -> Optional[IExtractor]:
        from urllib.parse import urlparse  # local import to keep stdlib only

        domain = urlparse(url).netloc.lower()
        site = self.registry.get_site_by_domain(domain)
        if not site:
            return None
        return self.get_extractor_by_site(site)

    def get_extractor_by_site(self, site_name: str) -> Optional[IExtractor]:
        if site_name not in self._instances:
            cls = self.registry.get_extractor_class(site_name)
            if cls is None:
                return None
            self._instances[site_name] = cls()  # type: ignore[call-arg]
        return self._instances[site_name]

    def clear_cache(self) -> None:
        self._instances.clear()


_factory_singleton: Optional[ExtractorFactory] = None


def get_extractor_factory() -> ExtractorFactory:
    global _factory_singleton
    if _factory_singleton is None:
        _factory_singleton = ExtractorFactory(get_extractor_registry())
    return _factory_singleton


def register_extractor(site_name: str, domains: List[str]):
    """Decorator for easy registration."""

    def decorator(cls: Type[IExtractor]):
        get_extractor_registry().register(site_name, cls, domains)
        return cls

    return decorator
