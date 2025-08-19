import logging
import re
from typing import Dict
from urllib.parse import urljoin, urlparse
import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from proxy.video_proxy import VideoProxy
from proxy.config import get_domain_config

logger = logging.getLogger()


class PornhubProxy(VideoProxy):
    def _extract_domain_from_request(self) -> str:
        """返回Pornhub域名"""
        return "pornhub.com"

    @property
    def headers(self) -> Dict[str, str]:
        # 使用配置中的自定义headers，如果有的话
        domain_config = get_domain_config("pornhub.com")
        if domain_config and domain_config.custom_headers:
            return domain_config.custom_headers.copy()

        # 默认headers
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://www.pornhub.com/',
            'Origin': 'https://www.pornhub.com/'
        }
        
    async def handle_m3u8(self, url: str, content: bytes) -> StreamingResponse:
        """处理m3u8文件"""
        content_text = content.decode()
        base_url = url.rsplit('/', 1)[0]

        def replace_url(match):
            path = match.group(1)
            full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
            return f"/api/video/proxy?domain=pornhub.com&url={full_url}"

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
                connect=30.0,
                read=180.0,  # Long read timeout for large video files
                write=30.0,
                pool=10.0
            )

            # Enhanced client configuration
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

            async with httpx.AsyncClient(**client_config) as client:
                # Use enhanced headers with retry logic
                headers = self.headers.copy()

                # Parse URL to handle query parameters when detecting m3u8 resources
                parsed = urlparse(url)
                path_lower = parsed.path.lower()

                # For small files (like m3u8), use direct download
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
                    # For large files, use the parent class's enhanced streaming
                    return await super().handle_stream(url)

        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:
            logger.error(f"Error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")