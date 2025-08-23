import logging
import re
from urllib.parse import urljoin
import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from sites.proxy import VideoProxy
from sites.proxy_registry import register_proxy

logger = logging.getLogger()


@register_proxy
class JavdbProxy(VideoProxy):
    domain = 'javdb.com'

    async def handle_m3u8(self, url: str, content: bytes) -> StreamingResponse:
        """处理m3u8文件"""
        content_text = content.decode()
        base_url = url.rsplit('/', 1)[0]

        def replace_url(match):
            path = match.group(1)
            full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
            return f"/api/video/proxy?domain={self.domain}&url={full_url}"

        content_text = re.sub(
            r'([^"\n]+\.(ts|jpeg|jpg|m3u8)[^"\n]*)',
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

    async def handle_stream(self, url: str) -> StreamingResponse:
        try:
            # Enhanced timeout configuration for better network resilience
            timeout_config = httpx.Timeout(
                connect=45.0,  # Longer connect timeout for potentially slower servers
                read=150.0,    # Extended read timeout
                write=30.0,
                pool=10.0
            )

            # Enhanced client configuration
            client_config = {
                "timeout": timeout_config,
                "limits": httpx.Limits(
                    max_keepalive_connections=15,
                    max_connections=30,
                    keepalive_expiry=45.0
                ),
                "follow_redirects": True,
                "http2": True
            }

            async with httpx.AsyncClient(**client_config) as client:
                # Use enhanced headers with retry logic
                headers = self.proxy_config.get_site_headers()

                # For small files (like m3u8), use direct download
                if url.endswith('.m3u8') or 'playlist' in url.lower():
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    content = response.content
                    content_type = response.headers.get('content-type', '')

                    if url.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
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
                    return await super().handle_stream(url)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:
            logger.error(f"Error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")