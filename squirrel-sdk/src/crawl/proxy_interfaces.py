from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional, Type


class VideoProxyBase:
    domain: Optional[str] = None


class ProxyRegistry:
    _items: Dict[str, Type[VideoProxyBase]] = {}

    @classmethod
    def register(cls, proxy_class: Type[VideoProxyBase]):
        domain = getattr(proxy_class, 'domain', None)
        if not domain:
            raise AttributeError("Proxy must define 'domain'")
        cls._items[domain] = proxy_class
        return proxy_class

    @classmethod
    def get_proxy_class(cls, domain: str) -> Optional[Type[VideoProxyBase]]:
        return cls._items.get(domain)

    @classmethod
    def get_supported_domains(cls) -> list[str]:
        return list(cls._items.keys())


register_proxy = ProxyRegistry.register


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


class ProxyConfigProvider:
    domain: Optional[str] = None

    @classmethod
    def get_site_headers(cls) -> Dict[str, str]:
        return {}

    @classmethod
    def get_domain_configs(cls) -> list[ProxyDomainConfig]:
        return []


class ProxyConfigRegistry:
    _providers: Dict[str, Type[ProxyConfigProvider]] = {}

    @classmethod
    def register(cls, provider_cls: Type[ProxyConfigProvider]):
        domain = getattr(provider_cls, 'domain', None)
        if not domain:
            raise AttributeError("ProxyConfigProvider must define 'domain'")
        cls._providers[domain] = provider_cls
        return provider_cls

    @classmethod
    def get(cls, domain: str) -> Optional[Type[ProxyConfigProvider]]:
        return cls._providers.get(domain)


def register_site_config(provider_cls: Type[ProxyConfigProvider]):
    return ProxyConfigRegistry.register(provider_cls)

