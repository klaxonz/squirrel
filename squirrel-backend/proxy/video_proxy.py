import asyncio
import logging
import time
from typing import Dict, AsyncGenerator, Optional
from urllib.parse import urlparse

import httpx
from fastapi import Request, HTTPException
from starlette.responses import StreamingResponse

from proxy.network_utils import NetworkOptimizer, AdaptiveRetryStrategy, get_health_monitor
from proxy.config import get_domain_config, get_network_config

logger = logging.getLogger()


async def stream_with_retry(
        url: str,
        headers: Dict[str, str],
        chunk_size: int = 1024 * 512,
        max_retries: Optional[int] = None,
        timeout: float = 120.0,
        range_start: Optional[int] = None
) -> AsyncGenerator[bytes, None]:
    """
    Stream content with enhanced retry mechanism and resume capability

    Args:
        url: Target URL
        headers: Request headers
        chunk_size: Streaming chunk size
        max_retries: Maximum retry attempts
        timeout: Request timeout in seconds
        range_start: Starting byte position for range requests
    """
    if timeout <= 0:
        raise ValueError("Timeout must be positive")

    # Extract domain for optimization
    parsed_url = urlparse(url)
    domain = parsed_url.netloc.replace('www.', '')

    # Initialize adaptive retry strategy
    retry_strategy = AdaptiveRetryStrategy(domain)
    health_monitor = get_health_monitor()

    # Define non-retryable errors
    NON_RETRYABLE_ERRORS = (
        httpx.HTTPStatusError,  # Don't retry 4xx/5xx status codes
        ValueError,
        TypeError
    )

    last_exception = None
    bytes_received = range_start or 0

    # Get optimal timeout configuration
    connect_timeout, read_timeout, _ = NetworkOptimizer.get_optimal_timeout(
        domain, 0  # We don't know content length yet
    )

    # Enhanced timeout configuration
    timeout_config = httpx.Timeout(
        connect=connect_timeout,
        read=read_timeout,
        write=30.0,
        pool=10.0
    )

    # Enhanced client configuration for better network resilience
    client_config = {
        "timeout": timeout_config,
        "limits": httpx.Limits(
            max_keepalive_connections=20,
            max_connections=100,
            keepalive_expiry=30.0
        ),
        "follow_redirects": True,
        "http2": True  # Enable HTTP/2 for better performance
    }

    for attempt in range(retry_strategy.max_retries):
        request_start_time = time.time()
        try:
            # Prepare headers with range support for resume
            request_headers = headers.copy()
            if bytes_received > 0:
                request_headers['Range'] = f'bytes={bytes_received}-'
                logger.info(f"Resuming download from byte {bytes_received}")

            async with httpx.AsyncClient(**client_config) as client:
                async with client.stream("GET", url, headers=request_headers) as resp:
                    resp.raise_for_status()

                    total_size = int(resp.headers.get('content-length', 0))
                    if resp.status_code == 206:  # Partial content
                        content_range = resp.headers.get('content-range', '')
                        if content_range:
                            # Parse content-range: bytes start-end/total
                            parts = content_range.split('/')
                            if len(parts) == 2:
                                total_size = int(parts[1])

                    # Optimize chunk size using NetworkOptimizer
                    content_type = resp.headers.get('content-type', '')
                    optimal_chunk_size = NetworkOptimizer.get_optimal_chunk_size(
                        total_size, content_type
                    )
                    chunk_size = max(chunk_size, optimal_chunk_size)

                    chunk_count = 0
                    last_progress_log = 0
                    async for chunk in resp.aiter_bytes(chunk_size=chunk_size):
                        chunk_count += 1
                        bytes_received += len(chunk)

                        # Less frequent progress logging to reduce overhead
                        if total_size and bytes_received - last_progress_log > 10 * 1024 * 1024:  # Every 10MB
                            progress = (bytes_received / total_size) * 100
                            logger.debug(f"Download progress: {progress:.1f}% ({bytes_received}/{total_size} bytes)")
                            last_progress_log = bytes_received

                        yield chunk

                    # Record successful request
                    request_duration = time.time() - request_start_time
                    health_monitor.record_request(domain, True, request_duration)
                    retry_strategy.record_success()

                    logger.info(f"Stream completed: {bytes_received} bytes transferred in {request_duration:.2f}s")
                    return

        except NON_RETRYABLE_ERRORS as e:
            request_duration = time.time() - request_start_time
            health_monitor.record_request(domain, False, request_duration)
            retry_strategy.record_failure()
            logger.error(f"Non-retryable error occurred: {str(e)}")
            raise

        except Exception as e:
            request_duration = time.time() - request_start_time
            health_monitor.record_request(domain, False, request_duration)
            retry_strategy.record_failure()

            last_exception = e
            if not retry_strategy.should_retry(e, attempt) or attempt == retry_strategy.max_retries - 1:
                logger.error(
                    f"Failed after {attempt + 1} attempts: {str(e)}, "
                    f"URL: {url}, Bytes received: {bytes_received}"
                )
                raise last_exception

            # Use adaptive retry delay
            retry_delay = retry_strategy.get_delay(attempt)

            logger.warning(
                f"Attempt {attempt + 1}/{retry_strategy.max_retries} failed, retrying in {retry_delay:.1f}s: {str(e)}"
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

        # 从URL中提取域名以获取配置
        self._domain = self._extract_domain_from_request()
        domain_config = get_domain_config(self._domain)
        network_config = get_network_config()

        # 使用配置或默认值
        if domain_config:
            self._chunk_size = domain_config.chunk_size
            self._timeout = domain_config.read_timeout
            self._max_retries = domain_config.max_retries
            self._connect_timeout = domain_config.connect_timeout
        else:
            self._chunk_size = network_config.default_chunk_size
            self._timeout = network_config.default_read_timeout
            self._max_retries = network_config.default_max_retries
            self._connect_timeout = network_config.default_connect_timeout

    def _extract_domain_from_request(self) -> str:
        """从请求中提取域名"""
        # 这里可以从请求参数或其他方式获取域名
        # 暂时返回空字符串，子类可以重写
        return ""

    @property
    def headers(self) -> Dict[str, str]:
        raise NotImplementedError

    def _extract_range_info(self) -> Optional[int]:
        """Extract range start position from request headers (legacy helper)"""
        range_header = self._get_raw_range_header()
        if range_header and range_header.startswith('bytes='):
            try:
                range_part = range_header[6:]  # Remove 'bytes='
                if '-' in range_part:
                    start_str = range_part.split('-')[0]
                    if start_str:
                        return int(start_str)
            except (ValueError, IndexError):
                logger.warning(f"Invalid range header: {range_header}")
        return None

    def _get_raw_range_header(self) -> Optional[str]:
        """Return the raw Range header (preserve start-end) if present"""
        return next(
            (self.request.headers[key] for key in self.request.headers
             if key.lower() == 'range'),
            None
        )

    async def handle_stream(self, url: str) -> StreamingResponse:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
            follow_redirects=True,
            http2=True
        )

        upstream_headers = self.headers.copy()
        range_header = self._get_raw_range_header()
        if range_header:
            upstream_headers['Range'] = range_header

        async def stream_generator():
            try:
                async with client.stream("GET", url, headers=upstream_headers) as resp:
                    # First yield the status code and headers
                    yield {
                        "status_code": resp.status_code,
                        "headers": {
                            "Content-Type": resp.headers.get('Content-Type', 'application/octet-stream'),
                            "Content-Length": resp.headers.get('Content-Length'),
                            "Content-Range": resp.headers.get('Content-Range'),
                            "Accept-Ranges": "bytes",
                        }
                    }
                    # Then yield the content chunks
                    async for chunk in resp.aiter_bytes():
                        yield chunk
            except httpx.RequestError as exc:
                logger.error(f"An error occurred while requesting {exc.request.url!r}: {exc}")
                yield {"error": "Bad Gateway"}
            finally:
                await client.aclose()

        try:
            streamer = stream_generator()
            # The first item yielded is the header dict
            first_item = await streamer.__anext__()
            if "error" in first_item:
                raise HTTPException(status_code=502, detail=first_item["error"])

            status_code = first_item["status_code"]
            headers = {k: v for k, v in first_item["headers"].items() if v is not None}

            return StreamingResponse(streamer, status_code=status_code, headers=headers)

        except Exception as e:
            logger.error(f"Unexpected error in proxy for {url}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail="Internal Server Error")
