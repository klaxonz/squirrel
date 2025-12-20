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
