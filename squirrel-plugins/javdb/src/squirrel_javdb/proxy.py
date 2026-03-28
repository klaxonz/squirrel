from __future__ import annotations

import logging
import re
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse

from crawl import get_http_headers, get_proxy_config

logger = logging.getLogger()

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
}


def _proxy_config_values() -> dict:
    config = dict(DEFAULT_PROXY_CONFIG)
    config.update(get_proxy_config(SITE_SLUG))
    return config


def build_runtime_proxy_config(domain: str | None = None) -> dict[str, object]:
    effective_domain = str(domain or SITE_DOMAIN).strip().lower() or SITE_DOMAIN
    config = _proxy_config_values()
    return {
        'site_headers': get_http_headers(SITE_SLUG, DEFAULT_SITE_HEADERS),
        'domain_configs': [{
            'domain': effective_domain,
            'connect_timeout': float(config['connect_timeout']),
            'read_timeout': float(config['read_timeout']),
            'max_retries': int(config['max_retries']),
            'chunk_size': int(config['chunk_size']),
            'max_connections': int(config['max_connections']),
            'keepalive_expiry': float(config['keepalive_expiry']),
            'enable_http2': bool(config['enable_http2']),
        }],
    }


def rewrite_proxy_playlist(url: str, content: str | bytes, referer: str | None = None) -> dict[str, object]:
    content_text = content.decode(errors='ignore') if isinstance(content, (bytes, bytearray)) else str(content)
    base_url = url.rsplit('/', 1)[0]

    def replace_url(match):
        path = match.group(1)
        full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
        query = urlencode({
            'domain': SITE_DOMAIN,
            'url': full_url,
            **({'referer': referer} if referer else {}),
        })
        return f'/api/video/proxy?{query}'

    rewritten = re.sub(
        r'([^"\n]+\.(ts|m4s|mp4|jpeg|jpg|m3u8)[^"\n]*)',
        replace_url,
        content_text,
    )

    return {
        'content': rewritten,
        'media_type': 'application/vnd.apple.mpegurl',
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'no-cache',
        },
    }


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
        except Exception as e:
            logger.error(f'Error occurred while proxying {url}: {str(e)}')
            raise HTTPException(status_code=500, detail=f'Internal server error: {str(e)}')
