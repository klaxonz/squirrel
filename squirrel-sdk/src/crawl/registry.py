"""Extractor plugin registry for Squirrel Crawl SDK."""
from __future__ import annotations

from threading import RLock
from typing import Callable, Dict, List, Optional, Type

from .interfaces import IExtractor, ISubscription, LoginStatusResult


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


# ---------------- Subscription registry -----------------


class SubscriptionRegistry:
    """Keep track of registered subscription classes by domain and site name."""

    def __init__(self) -> None:
        self._by_domain: Dict[str, Type[ISubscription]] = {}
        self._by_site: Dict[str, Type[ISubscription]] = {}
        self._lock = RLock()

    def register(self, site_name: str, domains: List[str], cls: Type[ISubscription]) -> None:
        with self._lock:
            if site_name in self._by_site:
                raise ValueError(f"Subscription already registered for site: {site_name}")
            self._by_site[site_name] = cls
            for d in domains:
                self._by_domain[d] = cls

    def get_by_domain(self, domain: str) -> Optional[Type[ISubscription]]:
        return self._by_domain.get(domain)

    def get_by_site(self, site_name: str) -> Optional[Type[ISubscription]]:
        return self._by_site.get(site_name)

    def get_supported_domains(self) -> List[str]:
        return list(self._by_domain.keys())


_subscription_registry_singleton: Optional[SubscriptionRegistry] = None


def get_subscription_registry() -> SubscriptionRegistry:
    global _subscription_registry_singleton
    if _subscription_registry_singleton is None:
        _subscription_registry_singleton = SubscriptionRegistry()
    return _subscription_registry_singleton


class SubscriptionFactory:
    """Create subscription instances by URL (domain) or site name."""

    @staticmethod
    def create_subscription(url: str) -> ISubscription:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # try most specific to least specific by splitting dots
        parts = domain.split('.')
        reg = get_subscription_registry()
        for i in range(len(parts) - 1):
            d = '.'.join(parts[i:])
            cls = reg.get_by_domain(d)
            if cls:
                return cls(url)  # type: ignore[call-arg]
        raise ValueError(f"Unsupported url: {url}")

    @staticmethod
    def get_supported_domains() -> List[str]:
        return get_subscription_registry().get_supported_domains()


def register_subscription(site_name: str, domains: List[str]):
    def decorator(cls: Type[ISubscription]):
        get_subscription_registry().register(site_name, domains, cls)
        return cls

    return decorator


# ---------------- User Subscription Importer registry -----------------


class UserSubscriptionImporterRegistry:
    """Keep track of registered user subscription importer classes by site name."""

    def __init__(self) -> None:
        self._by_site: Dict[str, Type] = {}
        self._lock = RLock()

    def register(self, site_name: str, cls: Type) -> None:
        with self._lock:
            if site_name in self._by_site:
                raise ValueError(f"Importer already registered for site: {site_name}")
            self._by_site[site_name] = cls

    def get_by_site(self, site_name: str) -> Optional[Type]:
        return self._by_site.get(site_name)

    def get_supported_sites(self) -> List[str]:
        return list(self._by_site.keys())


_importer_registry_singleton: Optional[UserSubscriptionImporterRegistry] = None


def get_importer_registry() -> UserSubscriptionImporterRegistry:
    global _importer_registry_singleton
    if _importer_registry_singleton is None:
        _importer_registry_singleton = UserSubscriptionImporterRegistry()
    return _importer_registry_singleton


def register_user_subscription_importer(site_name: str):
    """Decorator for registering a user subscription importer."""
    def decorator(cls: Type):
        get_importer_registry().register(site_name, cls)
        return cls
    return decorator


# ---------------- Login status checker registry -----------------

LoginStatusChecker = Callable[[], LoginStatusResult]


class LoginStatusCheckerRegistry:
    """Registry for optional site login status checkers."""

    def __init__(self) -> None:
        self._by_site: Dict[str, LoginStatusChecker] = {}
        self._lock = RLock()

    def register(self, site_name: str, checker: LoginStatusChecker) -> None:
        if not callable(checker):
            raise TypeError("login checker must be callable")
        with self._lock:
            self._by_site[site_name] = checker

    def get(self, site_name: str) -> Optional[LoginStatusChecker]:
        return self._by_site.get(site_name)

    def get_supported_sites(self) -> List[str]:
        return list(self._by_site.keys())


_login_checker_registry_singleton: Optional[LoginStatusCheckerRegistry] = None


def get_login_checker_registry() -> LoginStatusCheckerRegistry:
    global _login_checker_registry_singleton
    if _login_checker_registry_singleton is None:
        _login_checker_registry_singleton = LoginStatusCheckerRegistry()
    return _login_checker_registry_singleton


def register_login_checker(site_name: str):
    """Decorator for registering a site login status checker."""
    def decorator(func: LoginStatusChecker):
        get_login_checker_registry().register(site_name, func)
        return func
    return decorator
