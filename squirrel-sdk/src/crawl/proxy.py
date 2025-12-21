from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable, Type

from .registries import PluginRegistry, get_registry_manager


@runtime_checkable
class VideoProxy(Protocol):
    """Protocol for video proxy handlers."""

    domains: List[str]

    async def handle_stream(self, url: str) -> Callable:
        """Handle a video stream request and return a callable handler."""
        ...


def get_proxy_registry() -> PluginRegistry[Type[VideoProxy]]:
    """Get the global proxy registry."""
    return get_registry_manager().proxy


def register_proxy(domains_or_cls=None):
    """Decorator to register a video proxy.

    Usage:
        # Method 1: Auto-detect domains from class attribute
        @register_proxy
        class MyProxy:
            domains = ["example.com"]
            ...

        # Method 2: Explicitly specify domains
        @register_proxy(["example.com"])
        class MyProxy:
            domains = ["example.com"]
            ...
    """
    def decorator(proxy_class: Type[VideoProxy]):
        if isinstance(domains_or_cls, list):
            domains = domains_or_cls
        else:
            domains = getattr(proxy_class, 'domains', None)
            if not domains:
                domain = getattr(proxy_class, 'domain', None)
                domains = [domain] if domain else None

        if not domains:
            raise AttributeError("Proxy must define 'domains' attribute")

        registry = get_proxy_registry()
        key = domains[0]
        registry.register(key, proxy_class, domains)
        return proxy_class

    if domains_or_cls is not None and not isinstance(domains_or_cls, list):
        return decorator(domains_or_cls)

    return decorator


ProxyConfig = Dict[str, Dict[str, Any]]


@dataclass
class ProxyDomainConfig:
    domain: str
    connect_timeout: float
    read_timeout: float
    max_retries: int
    chunk_size: int
    max_connections: int
    keepalive_expiry: float
    enable_http2: bool = True


@runtime_checkable
class ProxyConfigProvider(Protocol):
    """Protocol for proxy configuration providers."""

    domains: List[str]

    @classmethod
    def get_site_headers(cls) -> Dict[str, str]:
        """Get site-specific HTTP headers for proxy requests."""
        ...

    @classmethod
    def get_domain_configs(cls) -> List[ProxyDomainConfig]:
        """Get domain-specific proxy configurations."""
        ...


def get_proxy_config_registry() -> PluginRegistry[Type[ProxyConfigProvider]]:
    """Get the global proxy config provider registry."""
    return get_registry_manager().proxy_config


def register_site_config(domains_or_cls=None):
    """Decorator to register a proxy config provider.

    Usage:
        # Method 1: Auto-detect domains from class attribute
        @register_site_config
        class MyProxyConfigProvider:
            domains = ["example.com"]
            ...

        # Method 2: Explicitly specify domains
        @register_site_config(["example.com"])
        class MyProxyConfigProvider:
            domains = ["example.com"]
            ...
    """
    def decorator(provider_cls: Type[ProxyConfigProvider]):
        if isinstance(domains_or_cls, list):
            domains = domains_or_cls
        else:
            domains = getattr(provider_cls, 'domains', None)
            if not domains:
                domain = getattr(provider_cls, 'domain', None)
                domains = [domain] if domain else None

        if not domains:
            raise AttributeError("ProxyConfigProvider must define 'domains' attribute")

        registry = get_proxy_config_registry()
        key = domains[0]
        registry.register(key, provider_cls, domains)
        return provider_cls

    if domains_or_cls is not None and not isinstance(domains_or_cls, list):
        return decorator(domains_or_cls)

    return decorator


DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def create_site_config(
    domain: str,
    referer: Optional[str] = None,
    user_agent: Optional[str] = None,
    connect_timeout: float = 30.0,
    read_timeout: float = 120.0,
    max_retries: int = 5,
    chunk_size: int = 2 * 1024 * 1024,
    max_connections: int = 50,
    keepalive_expiry: float = 30.0,
    enable_http2: bool = True,
    extra_headers: Optional[Dict[str, str]] = None,
) -> Type[ProxyConfigProvider]:
    """Factory function to create and register a site config provider.

    This eliminates boilerplate code in plugins. Instead of defining a full class,
    plugins can use this one-liner:

        create_site_config('pornhub.com', referer='https://www.pornhub.com')

    Args:
        domain: The domain this config applies to (e.g., 'youtube.com')
        referer: The Referer header value (defaults to https://{domain})
        user_agent: Custom User-Agent (defaults to Chrome UA)
        connect_timeout: Connection timeout in seconds
        read_timeout: Read timeout in seconds
        max_retries: Maximum retry attempts
        chunk_size: Download chunk size in bytes
        max_connections: Maximum concurrent connections
        keepalive_expiry: Keep-alive expiry in seconds
        enable_http2: Whether to enable HTTP/2
        extra_headers: Additional headers to include

    Returns:
        The created and registered ProxyConfigProvider class
    """
    _referer = referer or f"https://{domain}"
    _user_agent = user_agent or DEFAULT_USER_AGENT
    _extra_headers = extra_headers or {}

    class _GeneratedProxyConfig:
        domains = [domain]

    @classmethod
    def _get_site_headers(cls) -> Dict[str, str]:
        headers = {
            "User-Agent": _user_agent,
            "Referer": _referer,
        }
        headers.update(_extra_headers)
        return headers

    @classmethod
    def _get_domain_configs(cls) -> List[ProxyDomainConfig]:
        return [
            ProxyDomainConfig(
                domain=domain,
                connect_timeout=connect_timeout,
                read_timeout=read_timeout,
                max_retries=max_retries,
                chunk_size=chunk_size,
                max_connections=max_connections,
                keepalive_expiry=keepalive_expiry,
                enable_http2=enable_http2,
            )
        ]

    _GeneratedProxyConfig.get_site_headers = _get_site_headers
    _GeneratedProxyConfig.get_domain_configs = _get_domain_configs

    registry = get_proxy_config_registry()
    registry.register(domain, _GeneratedProxyConfig, [domain])

    return _GeneratedProxyConfig
