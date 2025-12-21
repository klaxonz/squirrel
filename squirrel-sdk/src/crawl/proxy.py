from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Protocol, runtime_checkable, Type

from .registry import PluginRegistry


@runtime_checkable
class VideoProxy(Protocol):
    """Protocol for video proxy handlers."""
    
    domain: Optional[str]
    
    async def handle_stream(self, url: str) -> Callable:
        """Handle a video stream request and return a callable handler."""
        ...


# Global registry
_proxy_registry: Optional[PluginRegistry[Type[VideoProxy]]] = None


def get_proxy_registry() -> PluginRegistry[Type[VideoProxy]]:
    """Get the global proxy registry."""
    global _proxy_registry
    if _proxy_registry is None:
        _proxy_registry = PluginRegistry[Type[VideoProxy]]("ProxyRegistry")
    return _proxy_registry


def register_proxy(domain_or_cls=None):
    """Decorator to register a video proxy.

    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_proxy
        class MyProxy:
            domain = "example.com"
            ...

        # Method 2: Explicitly specify domain
        @register_proxy("example.com")
        class MyProxy:
            domain = "example.com"
            ...
    """
    def decorator(proxy_class: Type[VideoProxy]):
        if isinstance(domain_or_cls, str):
            domain_attr = domain_or_cls
        else:
            domain_attr = getattr(proxy_class, 'domain', None)

        if not domain_attr:
            raise AttributeError("Proxy must define 'domain' attribute")

        registry = get_proxy_registry()
        registry.register(domain_attr, proxy_class, [domain_attr])
        return proxy_class

    # If called without parentheses, domain_or_cls is the class itself
    if domain_or_cls is not None and not isinstance(domain_or_cls, str):
        return decorator(domain_or_cls)

    # If called with parentheses (with or without domain argument)
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
    
    domain: Optional[str]
    
    @classmethod
    def get_site_headers(cls) -> Dict[str, str]:
        """Get site-specific HTTP headers for proxy requests."""
        ...
    
    @classmethod
    def get_domain_configs(cls) -> List[ProxyDomainConfig]:
        """Get domain-specific proxy configurations."""
        ...


# Global registry for proxy config providers
_proxy_config_registry: Optional[PluginRegistry[Type[ProxyConfigProvider]]] = None


def get_proxy_config_registry() -> PluginRegistry[Type[ProxyConfigProvider]]:
    """Get the global proxy config provider registry."""
    global _proxy_config_registry
    if _proxy_config_registry is None:
        _proxy_config_registry = PluginRegistry[Type[ProxyConfigProvider]]("ProxyConfigRegistry")
    return _proxy_config_registry


def register_site_config(domain_or_cls=None):
    """Decorator to register a proxy config provider.

    Usage:
        # Method 1: Auto-detect domain from class attribute
        @register_site_config
        class MyProxyConfigProvider:
            domain = "example.com"
            ...

        # Method 2: Explicitly specify domain
        @register_site_config("example.com")
        class MyProxyConfigProvider:
            domain = "example.com"
            ...
    """
    def decorator(provider_cls: Type[ProxyConfigProvider]):
        if isinstance(domain_or_cls, str):
            domain_attr = domain_or_cls
        else:
            domain_attr = getattr(provider_cls, 'domain', None)

        if not domain_attr:
            raise AttributeError("ProxyConfigProvider must define 'domain' attribute")

        registry = get_proxy_config_registry()
        registry.register(domain_attr, provider_cls, [domain_attr])
        return provider_cls

    # If called without parentheses, domain_or_cls is the class itself
    if domain_or_cls is not None and not isinstance(domain_or_cls, str):
        return decorator(domain_or_cls)

    # If called with parentheses (with or without domain argument)
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
        pass

    _GeneratedProxyConfig.domain = domain

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
