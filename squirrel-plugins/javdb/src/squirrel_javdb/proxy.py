from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse, urlencode
import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from crawl import VideoProxy, register_proxy, get_http_headers, get_proxy_config, get_proxy_config_registry

logger = logging.getLogger()


SITE_SLUG = 'javdb'


@register_proxy
class JavdbProxy:
    """JavDB视频代理，实现VideoProxy Protocol"""
    
    domain = 'javdb.com'
    site_slug = SITE_SLUG

    async def handle_m3u8(self, url: str, content: bytes) -> StreamingResponse:
        content_text = content.decode(errors='ignore')
        base_url = url.rsplit('/', 1)[0]

        def replace_url(match):
            path = match.group(1)
            full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
            query = urlencode({
                'domain': self.domain,
                'url': full_url,
            })
            return f"/api/video/proxy?{query}"

        content_text = re.sub(
            r'([^"\n]+\.(ts|m4s|mp4|jpeg|jpg|m3u8)[^"\n]*)',
            replace_url,
            content_text
        )

        return StreamingResponse(
            iter([content_text.encode()]),
            media_type='application/vnd.apple.mpegurl',
            headers={
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache',
            }
        )

    def _build_client_params(self):
        proxy_cfg = get_proxy_config(self.site_slug)
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

    async def handle_stream(self, url: str, **kwargs) -> StreamingResponse:
        try:
            timeout_config, limits, follow_redirects, http2_enabled = self._build_client_params()

            client_config = {
                "timeout": timeout_config,
                "limits": limits,
                "follow_redirects": follow_redirects,
                "http2": http2_enabled,
            }

            # Build headers from registered site config
            proxy_config_registry = get_proxy_config_registry()
            provider_cls = proxy_config_registry.get(self.domain)
            headers = get_http_headers(
                self.site_slug,
                (provider_cls.get_site_headers() or {}) if provider_cls else {},
            )

            async with httpx.AsyncClient(**client_config) as client:
                parsed = urlparse(url)
                path_lower = parsed.path.lower()

                if path_lower.endswith('.m3u8') or 'playlist' in url.lower():
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get('content-type', '')

                    if path_lower.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
                        return await self.handle_m3u8(url, content)

                    return StreamingResponse(
                        iter([content]),
                        media_type=content_type or 'application/octet-stream',
                        headers={
                            'Access-Control-Allow-Origin': '*',
                            'Cache-Control': 'public, max-age=3600',
                        }
                    )
                else:
                    # Fallback: direct stream without rewriting
                    resp = await client.get(url, headers=headers)
                    resp.raise_for_status()
                    return StreamingResponse(
                        resp.aiter_bytes(),
                        media_type=resp.headers.get('content-type', 'application/octet-stream'),
                        headers={
                            k: v for k, v in resp.headers.items()
                            if k.lower() in {
                                'content-type', 'content-length', 'content-range',
                                'accept-ranges', 'last-modified', 'etag', 'cache-control'
                            }
                        }
                    )

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:
            logger.error(f"Error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
