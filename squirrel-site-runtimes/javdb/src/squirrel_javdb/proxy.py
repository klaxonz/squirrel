from __future__ import annotations

import logging
from urllib.parse import urlparse

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from crawl import (
    build_proxy_config_values,
    build_runtime_proxy_config as build_shared_runtime_proxy_config,
    rewrite_playlist_for_proxy,
)

logger = logging.getLogger(__name__)

SITE_SLUG = 'javdb'
SITE_DOMAIN = 'javdb.com'
DEFAULT_SITE_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Referer': 'https://javdb.com/',
}
DEFAULT_PROXY_CONFIG = {
    'connect_timeout': 30.0,
    'read_timeout': 180.0,
    'write_timeout': 30.0,
    'pool_timeout': 30.0,
    'chunk_size': 2 * 1024 * 1024,
    'max_retries': 5,
    'max_keepalive_connections': 20,
    'max_connections': 40,
    'keepalive_expiry': 60.0,
    'follow_redirects': True,
    'enable_http2': True,
    'bypass_mode': 'mirror',
}


def _proxy_config_values() -> dict:
    return build_proxy_config_values(SITE_SLUG, DEFAULT_PROXY_CONFIG)


def _requires_cross_host_bypass(target_url: str) -> bool:
    path_lower = str(urlparse(target_url).path or '').strip().lower()
    return path_lower.endswith('.m3u8')


def build_runtime_proxy_config(payload: object | None = None) -> dict[str, object]:
    config = build_shared_runtime_proxy_config(
        site_slug=SITE_SLUG,
        site_domain=SITE_DOMAIN,
        default_site_headers=DEFAULT_SITE_HEADERS,
        default_proxy_config=DEFAULT_PROXY_CONFIG,
        domain=payload,
    )

    if isinstance(payload, dict):
        target_url = str(payload.get('target_url') or '').strip()
        target_host = str(urlparse(target_url).hostname or '').strip().lower()
        if (
            target_host
            and target_host != SITE_DOMAIN
            and not target_host.endswith(f'.{SITE_DOMAIN}')
            and _requires_cross_host_bypass(target_url)
        ):
            domain_configs = config.get('domain_configs')
            if isinstance(domain_configs, list) and domain_configs:
                first_config = domain_configs[0]
                if isinstance(first_config, dict):
                    first_config['bypass_domains'] = [target_host]

    return config


def rewrite_proxy_playlist(url: str, content: str | bytes, referer: str | None = None) -> dict[str, object]:
    return rewrite_playlist_for_proxy(
        url=url,
        content=content,
        site_domain=SITE_DOMAIN,
        referer=referer,
        extensions=('ts', 'm4s', 'mp4', 'jpeg', 'jpg', 'm3u8'),
    )


class JavdbProxy:
    """JavDB video proxy implementation."""

    domain = SITE_DOMAIN
    site_slug = SITE_SLUG

    async def handle_m3u8(self, url: str, content: bytes, referer: str | None = None) -> StreamingResponse:
        rewritten = rewrite_proxy_playlist(url, content, referer=referer)
        return StreamingResponse(
            iter([str(rewritten['content']).encode()]),
            media_type=str(rewritten['media_type']),
            headers=dict(rewritten['headers']),
        )

    def _build_client_params(self):
        proxy_cfg = _proxy_config_values()
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

    def _build_upstream_headers(self, referer: str | None = None) -> dict[str, str]:
        headers = dict(build_runtime_proxy_config(self.domain)['site_headers'])

        request = getattr(self, '_request', None)
        if request is not None:
            range_header = request.headers.get('range')
            if range_header:
                headers['Range'] = range_header

        headers.setdefault('Accept', '*/*')
        headers.setdefault('Cache-Control', 'no-cache')
        headers.setdefault('Pragma', 'no-cache')

        effective_referer = referer or headers.get('Referer') or headers.get('referer')
        if effective_referer:
            headers['Referer'] = effective_referer
            parsed = urlparse(effective_referer)
            if parsed.scheme and parsed.netloc:
                headers['Origin'] = f'{parsed.scheme}://{parsed.netloc}'

        return headers

    async def handle_stream(self, url: str, **kwargs) -> StreamingResponse:
        try:
            timeout_config, limits, follow_redirects, http2_enabled = self._build_client_params()

            client_config = {
                'timeout': timeout_config,
                'limits': limits,
                'follow_redirects': follow_redirects,
                'http2': http2_enabled,
            }

            upstream_referer = kwargs.get('referer')
            headers = self._build_upstream_headers(upstream_referer)

            async with httpx.AsyncClient(**client_config) as client:
                parsed = urlparse(url)
                path_lower = parsed.path.lower()

                if path_lower.endswith('.m3u8') or 'playlist' in url.lower():
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get('content-type', '')

                    if path_lower.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
                        return await self.handle_m3u8(url, content, referer=upstream_referer)

                    return StreamingResponse(
                        iter([content]),
                        media_type=content_type or 'application/octet-stream',
                        headers={
                            'Access-Control-Allow-Origin': '*',
                            'Cache-Control': 'public, max-age=3600',
                        },
                    )

                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                return StreamingResponse(
                    resp.aiter_bytes(),
                    media_type=resp.headers.get('content-type', 'application/octet-stream'),
                    headers={
                        k: v for k, v in resp.headers.items()
                        if k.lower() in {
                            'content-type',
                            'content-length',
                            'content-range',
                            'accept-ranges',
                            'last-modified',
                            'etag',
                            'cache-control',
                        }
                    },
                )

        except httpx.HTTPError as e:
            logger.error(f'HTTP error occurred while proxying {url}: {str(e)}')
            raise HTTPException(status_code=502, detail=f'Error fetching content: {str(e)}')
        except Exception as e:  # HTTP handler boundary — unexpected errors return 500
            logger.error(f'Error occurred while proxying {url}: {str(e)}')
            raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
