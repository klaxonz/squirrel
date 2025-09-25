import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional, Dict, AsyncIterator, Tuple
from urllib.parse import urlparse
import httpx
from fastapi import Request
from starlette.responses import StreamingResponse

from core.exceptions.proxy_exceptions import (
    ProxyException,
    ProxyTimeoutException,
    ProxyNetworkException,
    ProxyConfigurationException,
    UnsupportedDomainException
)
from crawl import ProxyConfigProvider, ProxyRegistry, VideoProxyBase

logger = logging.getLogger()


@dataclass
class ProxyMetrics:
    """代理性能指标"""
    request_count: int = 0
    total_bytes: int = 0
    total_duration: float = 0.0
    error_count: int = 0
    last_request_time: Optional[float] = None

    def record_request(self, bytes_transferred: int, duration: float, success: bool = True):
        """记录请求指标"""
        self.request_count += 1
        self.total_bytes += bytes_transferred
        self.total_duration += duration
        self.last_request_time = time.time()
        if not success:
            self.error_count += 1

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.request_count == 0:
            return 0.0
        return (self.request_count - self.error_count) / self.request_count

    @property
    def average_speed(self) -> float:
        """平均传输速度 (bytes/second)"""
        if self.total_duration == 0:
            return 0.0
        return self.total_bytes / self.total_duration


@dataclass
class ProxyRequest:
    """代理请求配置"""
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 120.0
    max_retries: int = 3
    chunk_size: int = 8192
    follow_redirects: bool = True
    enable_http2: bool = True

    def __post_init__(self):
        """验证请求参数"""
        if not self.url:
            raise ValueError("URL cannot be empty")

        parsed = urlparse(self.url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {self.url}")


class ConnectionManager:
    """HTTP连接管理器"""

    def __init__(self):
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._lock = asyncio.Lock()

    async def get_client(self, domain: str, proxy_config) -> httpx.AsyncClient:
        """获取或创建HTTP客户端"""
        async with self._lock:
            if domain not in self._clients:
                try:
                    client_config = proxy_config.get_client_config()
                    self._clients[domain] = httpx.AsyncClient(**client_config)
                    logger.debug(f"Created new HTTP client for domain: {domain}")
                except Exception as e:
                    logger.error(f"Failed to create HTTP client for {domain}: {e}")
                    raise ProxyConfigurationException(domain, str(e))

            return self._clients[domain]

    async def close_client(self, domain: str):
        """关闭指定域名的客户端"""
        async with self._lock:
            if domain in self._clients:
                await self._clients[domain].aclose()
                del self._clients[domain]
                logger.debug(f"Closed HTTP client for domain: {domain}")

    async def close_all(self):
        """关闭所有客户端"""
        async with self._lock:
            for domain, client in self._clients.items():
                try:
                    await client.aclose()
                    logger.debug(f"Closed HTTP client for domain: {domain}")
                except Exception as e:
                    logger.warning(f"Error closing client for {domain}: {e}")
            self._clients.clear()

    async def health_check(self, domain: str) -> bool:
        """检查连接健康状态"""
        if domain not in self._clients:
            return False

        client = self._clients[domain]
        return not client.is_closed


class VideoProxy(VideoProxyBase):
    """视频代理基类 - 重构版本"""

    domain: Optional[str] = None
    _connection_manager = ConnectionManager()
    _metrics: Dict[str, ProxyMetrics] = {}

    def __init__(self, request: Request):
        self.request = request
        self.domain = self.domain or self._extract_domain_from_request(request)
        if not self.domain:
            raise UnsupportedDomainException("unknown")

        provider_cls = ProxyConfigProvider.get(self.domain)  # type: ignore[attr-defined]
        if not provider_cls:
            raise ProxyConfigurationException(self.domain, "no proxy config provider")
        try:
            self.proxy_config = provider_cls()
        except Exception as e:
            raise ProxyConfigurationException(self.domain, str(e))

        # 初始化指标
        if self.domain not in self._metrics:
            self._metrics[self.domain] = ProxyMetrics()

    def _extract_domain_from_request(self, request: Request) -> Optional[str]:
        """从请求中提取域名"""
        # 可以从请求头、路径或查询参数中提取
        # 这里是一个基础实现，子类可以重写
        return None

    def _parse_range_header(self) -> Optional[Tuple[int, int]]:
        """解析Range头，返回(start, end)元组"""
        range_header = self.request.headers.get('range')
        if not range_header:
            return None

        try:
            # 解析 "bytes=start-end" 格式
            if range_header.startswith('bytes='):
                range_spec = range_header[6:]  # 移除 "bytes="
                if '-' in range_spec:
                    parts = range_spec.split('-', 1)
                    start = int(parts[0]) if parts[0] else 0
                    end = int(parts[1]) if parts[1] else None
                    return start, end
        except (ValueError, IndexError) as e:
            logger.warning(f"Invalid range header: {range_header}, error: {e}")

        return None

    def _build_upstream_headers(self, proxy_request: ProxyRequest) -> Dict[str, str]:
        headers = self.proxy_config.get_site_headers().copy()

        if 'range' in self.request.headers:
            headers['Range'] = self.request.headers['range']

        for header_name in ['user-agent', 'accept', 'accept-encoding']:
            if header_name in self.request.headers:
                headers[header_name] = self.request.headers[header_name]

        # 合并请求特定的头
        headers.update(proxy_request.headers)

        return headers

    async def _make_request_with_retry(self, client: httpx.AsyncClient,
                                       proxy_request: ProxyRequest) -> httpx.Response:
        headers = self._build_upstream_headers(proxy_request)
        last_exception = None

        for attempt in range(proxy_request.max_retries + 1):
            try:
                logger.debug(f"Attempting request to {proxy_request.url} (attempt {attempt + 1})")

                response = await client.get(
                    proxy_request.url,
                    headers=headers,
                    timeout=proxy_request.timeout,
                    follow_redirects=proxy_request.follow_redirects
                )

                # 检查响应状态
                if response.status_code >= 400:
                    if response.status_code in [404, 403, 401]:  # 不重试的错误
                        response.raise_for_status()
                    elif attempt < proxy_request.max_retries:  # 可重试的错误
                        logger.warning(f"HTTP {response.status_code} on attempt {attempt + 1}, retrying...")
                        await asyncio.sleep(2 ** attempt)  # 指数退避
                        continue
                    else:
                        response.raise_for_status()

                logger.debug(f"Successful request to {proxy_request.url} with status {response.status_code}")
                return response

            except httpx.TimeoutException as e:
                last_exception = ProxyTimeoutException(self.domain, proxy_request.timeout)
                logger.warning(f"Timeout on attempt {attempt + 1}: {e}")
            except httpx.NetworkError as e:
                last_exception = ProxyNetworkException(self.domain, str(e))
                logger.warning(f"Network error on attempt {attempt + 1}: {e}")
            except httpx.HTTPStatusError as e:
                raise ProxyNetworkException(self.domain, f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                last_exception = ProxyException(f"Unexpected error: {str(e)}", self.domain)
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)

            if attempt < proxy_request.max_retries:
                wait_time = min(2 ** attempt, 10)  # 最大等待10秒
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)

        if last_exception:
            raise last_exception
        raise ProxyException("All retry attempts failed", self.domain)

    async def _stream_response(self, response: httpx.Response,
                               chunk_size: int) -> AsyncIterator[bytes]:
        bytes_transferred = 0
        start_time = time.time()

        try:
            async for chunk in response.aiter_bytes(chunk_size):
                if chunk:
                    bytes_transferred += len(chunk)
                    yield chunk

            duration = time.time() - start_time
            self._metrics[self.domain].record_request(bytes_transferred, duration, True)
            logger.debug(f"Streamed {bytes_transferred} bytes in {duration:.2f}s")

        except Exception as e:
            duration = time.time() - start_time
            self._metrics[self.domain].record_request(bytes_transferred, duration, False)
            logger.error(f"Error during streaming: {e}")
            raise

    def _build_response_headers(self, upstream_response: httpx.Response) -> Dict[str, str]:
        """构建响应头"""
        headers = {}
        important_headers = [
            'content-type', 'content-length', 'content-range',
            'accept-ranges', 'last-modified', 'etag', 'cache-control'
        ]

        for header in important_headers:
            if header in upstream_response.headers:
                headers[header] = upstream_response.headers[header]

        if 'accept-ranges' not in headers:
            headers['accept-ranges'] = 'bytes'

        return headers

    @asynccontextmanager
    async def _get_http_client(self):
        client = await self._connection_manager.get_client(self.domain, self.proxy_config)
        try:
            yield client
        except Exception as e:
            logger.error(f"Error in HTTP client context: {e}")
            await self._connection_manager.close_client(self.domain)
            raise

    async def handle_stream(self, url: str, **kwargs) -> StreamingResponse:
        try:
            proxy_request = ProxyRequest(
                url=url,
                timeout=kwargs.get('timeout', 120.0),
                max_retries=kwargs.get('max_retries', 3),
                chunk_size=kwargs.get('chunk_size', 8192),
                **kwargs
            )

            logger.info(f"Starting proxy request: {self.domain} -> {url}")

            async with self._get_http_client() as client:
                response = await self._make_request_with_retry(client, proxy_request)
                response_headers = self._build_response_headers(response)
                stream = self._stream_response(response, proxy_request.chunk_size)

                logger.info(f"Proxy request successful: {response.status_code} for {url}")

                return StreamingResponse(
                    stream,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get('content-type', 'application/octet-stream')
                )

        except ProxyException:
            raise
        except Exception as e:
            logger.error(f"Unexpected error in handle_stream: {e}", exc_info=True)
            raise ProxyException(f"Internal proxy error: {str(e)}", self.domain, 500)

    @classmethod
    async def cleanup(cls):
        """清理所有连接"""
        await cls._connection_manager.close_all()
        logger.info("All proxy connections closed")


class ProxyFactory:

    @staticmethod
    def create_proxy(domain: str, request: Request) -> VideoProxy:
        try:
            proxy_class = ProxyRegistry.get_proxy_class(domain)
            if proxy_class:
                return proxy_class(request)

            raise UnsupportedDomainException(domain)

        except Exception as e:
            logger.error(f"Failed to create proxy for domain {domain}: {e}")
            if isinstance(e, ProxyException):
                raise
            raise ProxyConfigurationException(domain, str(e))

