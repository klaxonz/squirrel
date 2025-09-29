from __future__ import annotations

import logging
import re
from urllib.parse import urljoin, urlparse, urlencode

import httpx
from fastapi import HTTPException
from fastapi import Request
from starlette.responses import StreamingResponse

from crawl import VideoProxyBase, register_proxy
from crawl.proxy_interfaces import ProxyConfigRegistry

try:
    # Prefer backend utility that respects configured cookies file
    from utils.cookie import filter_cookies_to_query_string_by_domain as _cookie_for
except Exception:  # pragma: no cover - fallback in non-backend context
    from crawl import filter_cookies_to_query_string as _sdk_cookie_for

    def _cookie_for(domain_or_url: str) -> str:
        if not domain_or_url:
            return ""
        target = domain_or_url
        if "://" not in target:
            target = f"https://{str(domain_or_url).lstrip('.')}"
        try:
            return _sdk_cookie_for(target)
        except Exception:
            return ""


logger = logging.getLogger()


@register_proxy
class PornhubProxy(VideoProxyBase):
    domain = 'pornhub.com'

    def __init__(self, request: Request):
        super().__init__()

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

    async def handle_stream(self, url: str, **kwargs) -> StreamingResponse:
        try:
            timeout_config = httpx.Timeout(
                connect=30.0,
                read=180.0,
                write=30.0,
                pool=30.0
            )

            client_config = {
                "timeout": timeout_config,
                "limits": httpx.Limits(
                    max_keepalive_connections=20,
                    max_connections=40,
                    keepalive_expiry=60.0
                ),
                "follow_redirects": True,
                "http2": True
            }

            # Build headers from registered site config
            provider_cls = ProxyConfigRegistry.get(self.domain)
            headers = (provider_cls.get_site_headers() or {}) if provider_cls else {}
            headers.update({
                "Cookie": _cookie_for(url),
            })

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
