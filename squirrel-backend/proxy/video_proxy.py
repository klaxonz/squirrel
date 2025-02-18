import asyncio
import logging
from typing import Dict, AsyncGenerator
from urllib.parse import urlparse

import httpx
from fastapi import Request, HTTPException
from starlette.responses import StreamingResponse

logger = logging.getLogger()


async def stream_with_retry(
        url: str,
        headers: Dict[str, str],
        chunk_size: int = 1024 * 512,
        max_retries: int = 3,
        timeout: float = 60.0
) -> AsyncGenerator[bytes, None]:
    """
    Stream content with retry mechanism

    Args:
        url: Target URL
        headers: Request headers
        chunk_size: Streaming chunk size
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
    """
    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    # Define non-retryable errors
    NON_RETRYABLE_ERRORS = (
        httpx.HTTPStatusError,  # Don't retry 4xx/5xx status codes
        ValueError,
        TypeError
    )
    
    # Define retryable errors
    RETRYABLE_ERRORS = (
        httpx.NetworkError,
        httpx.TimeoutException,
        httpx.StreamClosed,
        httpx.RequestError,
        asyncio.TimeoutError
    )

    last_exception = None
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    total_size = int(resp.headers.get('content-length', 0))
                    bytes_received = 0

                    # Optimize chunk size for video/audio content
                    content_type = resp.headers.get('content-type', '')
                    if 'video' in content_type or 'audio' in content_type:
                        chunk_size = max(chunk_size, 1024 * 1024)  # Use larger chunks for media

                    async for chunk in resp.aiter_bytes(chunk_size=chunk_size):
                        bytes_received += len(chunk)
                        if total_size:
                            progress = (bytes_received / total_size) * 100
                            logger.debug(f"Download progress: {progress:.2f}%")
                        yield chunk

                    logger.info(f"Stream completed: {bytes_received} bytes transferred")
                    return

        except NON_RETRYABLE_ERRORS as e:
            logger.error(f"Non-retryable error occurred: {str(e)}")
            raise

        except RETRYABLE_ERRORS as e:
            last_exception = e
            if attempt == max_retries - 1:
                logger.error(
                    f"Failed after {max_retries} attempts: {str(e)}, "
                    f"URL: {url}, Status: {getattr(e, 'response', {}).get('status_code')}"
                )
                raise last_exception

            retry_delay = min(2 ** attempt, 10)
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s: {str(e)}"
            )
            await asyncio.sleep(retry_delay)


def _get_response_headers(resp: httpx.Response) -> Dict[str, str]:
    """获取响应头"""
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": resp.headers.get('Content-Type', 'application/octet-stream'),
    }
    for header in ['Content-Range', 'Content-Length']:
        if header in resp.headers:
            headers[header] = resp.headers[header]
    return headers


class VideoProxy:
    def __init__(self, request: Request):
        self.request = request
        self._chunk_size = 1024 * 1024 * 5
        self._timeout = 60.0

    @property
    def headers(self) -> Dict[str, str]:
        raise NotImplementedError

    async def handle_stream(self, url: str) -> StreamingResponse:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(self._timeout)) as client:
                headers = self.headers
                
                # Improved range request handling
                range_header = next(
                    (self.request.headers[key] for key in self.request.headers 
                     if key.lower() == 'range'),
                    None
                )
                if range_header:
                    headers['range'] = range_header

                async with client.stream("GET", url, headers=headers) as resp:
                    resp.raise_for_status()
                    
                    # Optimize chunk size based on content length
                    content_length = int(resp.headers.get('content-length', 0))
                    if content_length > 10 * 1024 * 1024:  # If file is larger than 10MB
                        self._chunk_size = 1024 * 1024  # Use 1MB chunks
                    
                    return StreamingResponse(
                        stream_with_retry(
                            url, 
                            headers,
                            chunk_size=self._chunk_size,
                            timeout=self._timeout
                        ),
                        status_code=resp.status_code,
                        headers=_get_response_headers(resp),
                        media_type=resp.headers.get('Content-Type')
                    )

        except httpx.HTTPStatusError as exc:
            logger.error(
                f"HTTP error occurred: {exc.response.status_code} "
                f"{exc.response.reason_phrase} for URL: {url}"
            )
            raise HTTPException(
                status_code=exc.response.status_code, 
                detail=exc.response.reason_phrase
            )
        except Exception as e:
            logger.error(
                f"Unexpected error while streaming {url}: {str(e)}",
                exc_info=True
            )
            raise HTTPException(
                status_code=500, 
                detail="Internal server error while streaming video"
            )
