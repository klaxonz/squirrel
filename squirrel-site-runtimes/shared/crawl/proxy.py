from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


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

    domains: list[str]

    @classmethod
    def get_site_headers(cls) -> dict[str, str]:
        """Get site-specific HTTP headers for proxy requests."""
        ...

    @classmethod
    def get_domain_configs(cls) -> list[ProxyDomainConfig]:
        """Get domain-specific proxy configurations."""
        ...
