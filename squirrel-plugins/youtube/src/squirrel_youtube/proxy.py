from __future__ import annotations

import logging
import re
from urllib.parse import urlencode, urljoin, urlparse

import httpx
from fastapi import HTTPException, Request
from starlette.responses import StreamingResponse

from crawl import VideoProxyBase, register_proxy
from crawl.proxy_interfaces import ProxyConfigRegistry

try:
    from utils.cookie import filter_cookies_to_query_string_by_domain as _cookie_for
except Exception:  # pragma: no cover
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


logger = logging.getLogger(__name__)


@register_proxy
class YouTubeProxy(VideoProxyBase):
    domain = 'youtube.com'

    def __init__(self, request: Request):
        super().__init__()
        self._request = request

    async def handle_m3u8(self, url: str, content: bytes) -> StreamingResponse:
        content_text = content.decode(errors='ignore')
        base_url = url.rsplit('/', 1)[0]

        def replace_url(match):
            path = match.group(1).strip()
            if not path or path.startswith('#'):
                return path
            full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
            query = urlencode({
                'domain': self.domain,
                'url': full_url,
            })
            return f"/api/video/proxy?{query}"

        content_text = re.sub(
            r'^(?!#)(.+\.(?:ts|m4s|mp4|m3u8|jpg|jpeg|vtt)[^\s]*)$',
            lambda m: replace_url(m),
            content_text,
            flags=re.MULTILINE
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
                    max_keepalive_connections=50,
                    max_connections=100,
                    keepalive_expiry=60.0
                ),
                "follow_redirects": True,
                "http2": True
            }

            provider_cls = ProxyConfigRegistry.get(self.domain)
            headers = (provider_cls.get_site_headers() or {}) if provider_cls else {}
            if self._request:
                range_header = self._request.headers.get('range')
                if range_header:
                    headers['Range'] = range_header
            headers.update({
                "Cookie": _cookie_for(url),
            })

            async with httpx.AsyncClient(**client_config) as client:
                parsed = urlparse(url)
                path_lower = parsed.path.lower()

                response = await client.get(url, headers=headers)
                response.raise_for_status()

                content_type = response.headers.get('content-type', '')
                if path_lower.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
                    return await self.handle_m3u8(url, response.content)

                forward_headers = {
                    k: v for k, v in response.headers.items()
                    if k.lower() in {
                        'content-type', 'content-length', 'content-range',
                        'accept-ranges', 'last-modified', 'etag', 'cache-control'
                    }
                }
                forward_headers.setdefault('Access-Control-Allow-Origin', '*')

                return StreamingResponse(
                    response.aiter_bytes(),
                    media_type=content_type or 'application/octet-stream',
                    headers=forward_headers
                )

        except httpx.HTTPStatusError as e:
            logger.error("YouTube proxy HTTP error for %s: %s", url, e)
            raise HTTPException(status_code=e.response.status_code, detail=f"Error fetching content: {str(e)}")
        except httpx.HTTPError as e:
            logger.error("YouTube proxy transport error for %s: %s", url, e)
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:  # pragma: no cover
            logger.exception("YouTube proxy unexpected error for %s", url)
            raise HTTPException(status_code=500, detail="Internal server error")
