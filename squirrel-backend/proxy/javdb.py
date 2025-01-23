import logging
import re
from typing import Dict
from urllib.parse import urljoin
import httpx
from fastapi import HTTPException
from starlette.responses import StreamingResponse
from proxy.video_proxy import VideoProxy

logger = logging.getLogger()


class JavdbProxy(VideoProxy):
    @property
    def headers(self) -> Dict[str, str]:
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Referer': 'https://missav.ai/',
            'Origin': 'https://missav.ai'
        }
        
    async def handle_m3u8(self, url: str, content: bytes) -> StreamingResponse:
        """处理m3u8文件"""
        content_text = content.decode()
        base_url = url.rsplit('/', 1)[0]

        def replace_url(match):
            path = match.group(1)
            full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
            return f"/api/video/proxy?domain=javdb.com&url={full_url}"

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
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=self.headers, follow_redirects=True)
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
                        'Cache-Control': 'public, max-age=31536000',
                    }
                )
        except httpx.HTTPError as e:
            logger.error(f"HTTP error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Error fetching content: {str(e)}")
        except Exception as e:
            logger.error(f"Error occurred while proxying {url}: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")