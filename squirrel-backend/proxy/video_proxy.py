import logging
from typing import Dict

import httpx
from fastapi import Request, HTTPException
from starlette.responses import StreamingResponse
from .utils import stream_with_retry

logger = logging.getLogger()


class VideoProxy:
    def __init__(self, request: Request):
        self.request = request

    @property
    def headers(self) -> Dict[str, str]:
        raise NotImplementedError

    async def handle_stream(self, url: str) -> StreamingResponse:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                headers = self.headers
                if "range" in self.request.headers:
                    headers["Range"] = self.request.headers["range"]

                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    return StreamingResponse(
                        stream_with_retry(url, headers),
                        status_code=resp.status_code,
                        headers=self._get_response_headers(resp)
                    )
        except httpx.HTTPStatusError as exc:
            logger.error(f"HTTP error occurred: {exc.response.status_code} {exc.response.reason_phrase}")
            raise HTTPException(status_code=exc.response.status_code, detail=exc.response.reason_phrase)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, detail="Internal server error")

    def _get_response_headers(self, resp: httpx.Response) -> Dict[str, str]:
        """获取响应头"""
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": resp.headers.get('Content-Type', 'application/octet-stream'),
        }
        for header in ['Content-Range', 'Content-Length']:
            if header in resp.headers:
                headers[header] = resp.headers[header]
        return headers
