from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class VideoProxy(Protocol):
    """Protocol for video proxy handlers."""

    domains: list[str]

    async def handle_stream(self, url: str) -> Callable:
        """Handle a video stream request and return a callable handler."""
        ...


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
