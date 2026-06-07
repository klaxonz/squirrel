from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from starlette.responses import StreamingResponse

from .playlist_rewrite import rewrite_playlist_for_proxy
from .proxy_helpers import build_proxy_config_values

logger = logging.getLogger(__name__)


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


class BaseSiteProxy:
    """Shared base for site proxy implementations.

    Subclasses define class-level config:

    - ``domain`` / ``site_slug``
    - ``default_proxy_config``
    - ``playlist_extensions`` (tuple of file extensions for playlist rewrite)

    Provides ``handle_m3u8``, ``_build_client_params``, ``_proxy_config_values``
    that are identical across all current site proxies.
    """

    domain: str = ''
    site_slug: str = ''
    default_proxy_config: dict[str, Any] = {}
    playlist_extensions: tuple[str, ...] = ('ts', 'm4s', 'mp4', 'jpeg', 'jpg', 'm3u8')

    def _proxy_config_values(self) -> dict:
        return build_proxy_config_values(self.site_slug, self.default_proxy_config)

    def _build_client_params(self):
        import httpx

        proxy_cfg = self._proxy_config_values()
        timeout_config = httpx.Timeout(
            connect=float(proxy_cfg.get('connect_timeout', 30.0)),
            read=float(proxy_cfg.get('read_timeout', 180.0)),
            write=float(proxy_cfg.get('write_timeout', 30.0)),
            pool=float(proxy_cfg.get('pool_timeout', 30.0)),
        )
        limits = httpx.Limits(
            max_keepalive_connections=int(proxy_cfg.get('max_keepalive_connections', 20)),
            max_connections=int(proxy_cfg.get('max_connections', 40)),
            keepalive_expiry=float(proxy_cfg.get('keepalive_expiry', 60.0)),
        )
        follow_redirects = bool(proxy_cfg.get('follow_redirects', True))
        http2_enabled = bool(proxy_cfg.get('enable_http2', True))
        return timeout_config, limits, follow_redirects, http2_enabled

    def _rewrite_proxy_playlist(self, url: str, content: str | bytes, referer: str | None = None) -> dict[str, object]:
        return rewrite_playlist_for_proxy(
            url=url,
            content=content,
            site_domain=self.domain,
            referer=referer,
            extensions=self.playlist_extensions,
        )

    async def handle_m3u8(self, url: str, content: bytes, referer: str | None = None) -> StreamingResponse:
        from starlette.responses import StreamingResponse as _StreamingResponse

        rewritten = self._rewrite_proxy_playlist(url, content, referer=referer)
        return _StreamingResponse(
            iter([str(rewritten['content']).encode()]),
            media_type=str(rewritten['media_type']),
            headers=dict(rewritten['headers']),
        )
