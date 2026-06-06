import asyncio
import inspect
import logging
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Optional, Dict, AsyncIterator, Any
from urllib.parse import urlparse
import httpx
from fastapi import Request
from starlette.responses import StreamingResponse

from core.exceptions.proxy_exceptions import (
    ProxyException,
    ProxyTimeoutException,
    ProxyNetworkException,
    ProxyConfigurationException,
    UnsupportedDomainException,
)
from site_runtimes.gateway import SiteRuntimeGateway
from site_runtimes.ports import get_runtime_gateway
from utils.cookie import filter_cookies_to_query_string
from utils.runtime_http import get_cloudflare_bypass_client

logger = logging.getLogger(__name__)


@dataclass
class ProxyRequest:
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    timeout: float = 120.0
    max_retries: int = 3
    chunk_size: int = 1024 * 1024  # 1MB for better streaming performance
    follow_redirects: bool = True

    def __post_init__(self):
        if not self.url:
            raise ValueError("URL cannot be empty")
        parsed = urlparse(self.url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {self.url}")


class RetryStrategy:
    TERMINAL_STATUS_CODES = {404, 403, 401, 416}

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def should_retry(self, attempt: int, status_code: Optional[int] = None) -> bool:
        if attempt >= self.max_retries:
            return False
        if status_code and status_code in self.TERMINAL_STATUS_CODES:
            return False
        return True

    def is_terminal_error(self, status_code: int) -> bool:
        return status_code in self.TERMINAL_STATUS_CODES

    def get_wait_time(self, attempt: int) -> float:
        return min(2 ** attempt, 10)


class HeaderBuilder:
    FORWARDED_HEADERS = ('user-agent', 'accept', 'accept-encoding', 'referer')

    @staticmethod
    def build_headers(
        request: Request,
        site_headers: Optional[Dict[str, str]],
        custom_headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        headers = {}
        
        if site_headers:
            headers.update(site_headers)

        if 'range' in request.headers:
            headers['Range'] = request.headers['range']

        for header_name in HeaderBuilder.FORWARDED_HEADERS:
            value = request.headers.get(header_name)
            if value:
                headers[header_name] = value

        if custom_headers:
            headers.update(custom_headers)

        return headers


class ResponseBuilder:
    IMPORTANT_HEADERS = [
        'content-type', 'content-length', 'content-range',
        'accept-ranges', 'last-modified', 'etag', 'cache-control',
    ]

    @staticmethod
    def build_response_headers(upstream_response: Any) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        for header in ResponseBuilder.IMPORTANT_HEADERS:
            if header in upstream_response.headers:
                headers[header] = upstream_response.headers[header]
        if 'accept-ranges' not in headers:
            headers['accept-ranges'] = 'bytes'
        return headers


class UpstreamResponseAdapter:
    @staticmethod
    async def read(response: Any) -> bytes:
        if hasattr(response, 'aread'):
            return await response.aread()
        content = getattr(response, 'content', b'')
        return content if isinstance(content, bytes) else bytes(content)

    @staticmethod
    async def close(response: Any) -> None:
        if hasattr(response, 'aclose'):
            await response.aclose()
            return
        close_fn = getattr(response, 'close', None)
        if callable(close_fn):
            close_fn()

    @staticmethod
    async def iter_bytes(response: Any, chunk_size: int) -> AsyncIterator[bytes]:
        if hasattr(response, 'aiter_bytes'):
            async for chunk in response.aiter_bytes(chunk_size):
                if chunk:
                    yield chunk
            return

        iter_content = getattr(response, 'iter_content', None)
        if callable(iter_content):
            for chunk in iter_content(chunk_size=chunk_size):
                if chunk:
                    yield chunk
            return

        body = await UpstreamResponseAdapter.read(response)
        if body:
            yield body

    @staticmethod
    def text(response: Any) -> str:
        text = getattr(response, 'text', None)
        if text is not None:
            return str(text)
        content = getattr(response, 'content', b'')
        if isinstance(content, bytes):
            return content.decode('utf-8', errors='ignore')
        return str(content)


class ConnectionManager:
    def __init__(self):
        self._clients: Dict[str, httpx.AsyncClient] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._main_lock = asyncio.Lock()

    def _build_client_config(self, domain_config: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if domain_config:
            connect_timeout = float(domain_config.get("connect_timeout", 10.0))
            read_timeout = float(domain_config.get("read_timeout", 120.0))
            max_connections = int(domain_config.get("max_connections", 50))
            keepalive_expiry = float(domain_config.get("keepalive_expiry", 30.0))
            enable_http2 = bool(domain_config.get("enable_http2", True))
        else:
            connect_timeout = 10.0
            read_timeout = 120.0
            max_connections = 50
            keepalive_expiry = 30.0
            enable_http2 = True

        return {
            "http2": enable_http2,
            "timeout": httpx.Timeout(
                connect=connect_timeout,
                read=read_timeout,
                write=read_timeout,
                pool=connect_timeout,
            ),
            "limits": httpx.Limits(
                max_keepalive_connections=max_connections,
                keepalive_expiry=keepalive_expiry,
            ),
            "follow_redirects": True,
        }

    async def get_client(self, domain: str, domain_config: Optional[Dict[str, Any]]) -> httpx.AsyncClient:
        if domain in self._clients:
            return self._clients[domain]

        async with self._main_lock:
            if domain not in self._locks:
                self._locks[domain] = asyncio.Lock()

        async with self._locks[domain]:
            if domain in self._clients:
                return self._clients[domain]

            try:
                client_config = self._build_client_config(domain_config)
                self._clients[domain] = httpx.AsyncClient(**client_config)
                logger.info(f"Created new HTTP client for domain: {domain}")
            except (ValueError, TypeError) as e:
                logger.error(f"Failed to create HTTP client for {domain}: {e}")
                raise ProxyConfigurationException(domain, str(e))

            return self._clients[domain]

    async def close_client(self, domain: str):
        async with self._main_lock:
            if domain in self._clients:
                await self._clients[domain].aclose()
                del self._clients[domain]
                if domain in self._locks:
                    del self._locks[domain]
                logger.debug(f"Closed HTTP client for domain: {domain}")

    async def close_all(self):
        async with self._main_lock:
            for domain, client in list(self._clients.items()):
                try:
                    await client.aclose()
                    logger.debug(f"Closed HTTP client for domain: {domain}")
                except Exception as e:  # cleanup during shutdown — must not propagate
                    logger.warning(f"Error closing client for {domain}: {e}")
            self._clients.clear()
            self._locks.clear()

    async def health_check(self, domain: str) -> bool:
        if domain not in self._clients:
            return False
        client = self._clients[domain]
        return not client.is_closed


class HttpRequester:
    def __init__(self, domain: str, retry_strategy: RetryStrategy):
        self.domain = domain
        self.retry_strategy = retry_strategy

    @staticmethod
    def _normalize_host(host_or_domain: Optional[str]) -> str:
        value = str(host_or_domain or '').strip().lower()
        if value.startswith('www.'):
            value = value[4:]
        return value

    @staticmethod
    def _bypass_mode(domain_config: Optional[Dict[str, Any]]) -> Optional[str]:
        mode = str((domain_config or {}).get('bypass_mode') or '').strip().lower()
        return mode if mode in {'html', 'mirror'} else None

    @classmethod
    def _bypass_domain(cls, domain_config: Optional[Dict[str, Any]], fallback_domain: str) -> str:
        configured_domain = ''
        if isinstance(domain_config, dict):
            configured_domain = cls._normalize_host(domain_config.get('domain'))
        return configured_domain or cls._normalize_host(fallback_domain)

    @classmethod
    def _bypass_hosts(cls, domain_config: Optional[Dict[str, Any]], fallback_domain: str) -> set[str]:
        hosts: set[str] = set()
        configured_domain = cls._bypass_domain(domain_config, fallback_domain)
        if configured_domain:
            hosts.add(configured_domain)

        if not isinstance(domain_config, dict):
            return hosts

        explicit_hosts = domain_config.get('bypass_domains')
        if not isinstance(explicit_hosts, (list, tuple, set)):
            explicit_hosts = [
                domain_config.get('bypass_domain'),
                domain_config.get('bypass_host'),
            ]

        for item in explicit_hosts:
            normalized = cls._normalize_host(item)
            if normalized:
                hosts.add(normalized)

        return hosts

    @classmethod
    def _should_bypass_request(
        cls,
        proxy_request: ProxyRequest,
        domain_config: Optional[Dict[str, Any]],
        fallback_domain: str,
    ) -> bool:
        configured_hosts = cls._bypass_hosts(domain_config, fallback_domain)
        if not configured_hosts:
            return False

        target_host = cls._normalize_host(urlparse(proxy_request.url).hostname)
        if not target_host:
            return False
        return any(
            target_host == configured_host or target_host.endswith(f'.{configured_host}')
            for configured_host in configured_hosts
        )

    async def _execute_bypass_request(
        self,
        proxy_request: ProxyRequest,
        headers: Dict[str, str],
        bypass_mode: str,
        *,
        stream: bool = False,
    ):
        client = get_cloudflare_bypass_client()
        if client is None:
            raise ProxyConfigurationException(self.domain, 'cloudflare bypass client is not configured')

        bypass_method = client.html if bypass_mode == 'html' else client.mirror
        kwargs = {'headers': headers}
        try:
            if 'stream' in inspect.signature(bypass_method).parameters:
                kwargs['stream'] = stream
        except (TypeError, ValueError):
            pass

        response = bypass_method(proxy_request.url, **kwargs)
        if inspect.isawaitable(response):
            return await response
        return response

    async def execute_request(
        self,
        client: httpx.AsyncClient,
        proxy_request: ProxyRequest,
        headers: Dict[str, str],
        domain_config: Optional[Dict[str, Any]] = None,
        stream: bool = False,
    ):
        last_exception = None
        bypass_mode = self._bypass_mode(domain_config)
        use_bypass = bool(bypass_mode) and self._should_bypass_request(proxy_request, domain_config, self.domain)

        for attempt in range(proxy_request.max_retries + 1):
            try:
                if use_bypass and bypass_mode:
                    response = await self._execute_bypass_request(
                        proxy_request,
                        headers,
                        bypass_mode,
                        stream=stream,
                    )
                else:
                    request = client.build_request(
                        'GET',
                        proxy_request.url,
                        headers=headers,
                        timeout=proxy_request.timeout,
                    )
                    response = await client.send(
                        request,
                        stream=stream,
                        follow_redirects=proxy_request.follow_redirects,
                    )

                if response.status_code >= 400:
                    await UpstreamResponseAdapter.read(response)
                    await UpstreamResponseAdapter.close(response)

                    if self.retry_strategy.is_terminal_error(response.status_code):
                        raise httpx.HTTPStatusError(
                            f'HTTP {response.status_code}',
                            request=None,
                            response=response,
                        )

                    if self.retry_strategy.should_retry(attempt, response.status_code):
                        logger.warning(f"HTTP {response.status_code} on attempt {attempt + 1}, retrying...")
                        await asyncio.sleep(self.retry_strategy.get_wait_time(attempt))
                        continue

                    raise httpx.HTTPStatusError(
                        f'HTTP {response.status_code}',
                        request=None,
                        response=response,
                    )

                return response

            except httpx.TimeoutException as e:
                last_exception = ProxyTimeoutException(self.domain, proxy_request.timeout)
                if attempt == proxy_request.max_retries:
                    logger.warning(f"Timeout after {attempt + 1} attempts: {e}")
            except httpx.NetworkError as e:
                last_exception = ProxyNetworkException(self.domain, str(e))
                if attempt == proxy_request.max_retries:
                    logger.warning(f"Network error after {attempt + 1} attempts: {e}")
            except httpx.HTTPStatusError as e:
                raise ProxyNetworkException(
                    self.domain,
                    f"HTTP {e.response.status_code}: {UpstreamResponseAdapter.text(e.response)}",
                )
            except (OSError, ValueError, TypeError) as e:
                last_exception = ProxyException(f"Unexpected error: {str(e)}", self.domain)
                logger.error(f"Unexpected error on attempt {attempt + 1}: {e}", exc_info=True)

            if self.retry_strategy.should_retry(attempt):
                await asyncio.sleep(self.retry_strategy.get_wait_time(attempt))

        if last_exception:
            raise last_exception
        raise ProxyException("All retry attempts failed", self.domain)


class VideoProxy:
    domain: Optional[str] = None
    _connection_manager = ConnectionManager()
    _runtime_config_cache: Dict[tuple[str, Optional[str], Optional[str]], tuple[float, Dict[str, str], Optional[Dict[str, Any]]]] = {}
    _runtime_config_cache_lock = threading.Lock()
    _runtime_config_cache_ttl = 5.0

    def __init__(
        self,
        request: Request,
        domain: Optional[str] = None,
        runtime_gateway: SiteRuntimeGateway | None = None,
    ):
        self.request = request
        self.domain = domain or self.domain or self._extract_domain_from_request(request)
        if not self.domain:
            raise UnsupportedDomainException("unknown")
        self.site_headers: Dict[str, str] = {}
        self.domain_config: Optional[Dict[str, Any]] = None
        self._runtime_gateway = runtime_gateway

    def _extract_domain_from_request(self, request: Request) -> Optional[str]:
        return None

    @classmethod
    def _runtime_config_cache_key(
        cls,
        domain: str,
        *,
        target_url: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> tuple[str, Optional[str], Optional[str]]:
        normalized_target_url = (str(target_url).strip() or None) if target_url else None
        normalized_referer = (str(referer).strip() or None) if referer else None
        return str(domain).strip().lower(), normalized_target_url, normalized_referer

    @classmethod
    def _get_cached_runtime_proxy_config(
        cls,
        domain: str,
        *,
        target_url: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> Optional[tuple[Dict[str, str], Optional[Dict[str, Any]]]]:
        cache_key = cls._runtime_config_cache_key(domain, target_url=target_url, referer=referer)
        now = time.monotonic()
        with cls._runtime_config_cache_lock:
            cached = cls._runtime_config_cache.get(cache_key)
            if cached is None:
                return None

            expires_at, site_headers, domain_config = cached
            if expires_at <= now:
                cls._runtime_config_cache.pop(cache_key, None)
                return None

            return dict(site_headers), dict(domain_config) if isinstance(domain_config, dict) else None

    @classmethod
    def _set_cached_runtime_proxy_config(
        cls,
        domain: str,
        *,
        target_url: Optional[str] = None,
        referer: Optional[str] = None,
        site_headers: Dict[str, str],
        domain_config: Optional[Dict[str, Any]],
    ) -> None:
        cache_key = cls._runtime_config_cache_key(domain, target_url=target_url, referer=referer)
        expires_at = time.monotonic() + float(cls._runtime_config_cache_ttl)
        cached_domain_config = dict(domain_config) if isinstance(domain_config, dict) else None
        with cls._runtime_config_cache_lock:
            cls._runtime_config_cache[cache_key] = (
                expires_at,
                dict(site_headers),
                cached_domain_config,
            )

    def _load_runtime_proxy_config(
        self,
        *,
        target_url: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> tuple[Dict[str, str], Optional[Dict[str, Any]]]:
        cached = self._get_cached_runtime_proxy_config(
            self.domain,
            target_url=target_url,
            referer=referer,
        )
        if cached is not None:
            return cached

        payload = {'domain': self.domain}
        if target_url:
            payload['target_url'] = target_url
        if referer:
            payload['referer'] = referer

        runtime_gateway = self._runtime_gateway or get_runtime_gateway()
        response = runtime_gateway.invoke(
            'resolve_proxy_config',
            domain=self.domain,
            payload=payload,
        )
        if not response.ok or not isinstance(response.data, dict):
            raise ProxyConfigurationException(self.domain, 'no runtime proxy config provider')

        payload = dict(response.data)
        domain_configs = payload.get('domain_configs') or []
        domain_config = None
        for item in domain_configs:
            if not isinstance(item, dict):
                continue
            if str(item.get('domain', '')).lower() == self.domain:
                domain_config = dict(item)
                break

        site_headers = dict(payload.get('site_headers') or {})
        self._set_cached_runtime_proxy_config(
            self.domain,
            target_url=target_url,
            referer=referer,
            site_headers=site_headers,
            domain_config=domain_config,
        )
        return site_headers, domain_config

    def _resolve_runtime_proxy_config(
        self,
        *,
        target_url: Optional[str] = None,
        referer: Optional[str] = None,
    ) -> tuple[Dict[str, str], Optional[Dict[str, Any]]]:
        site_headers, domain_config = self._load_runtime_proxy_config(target_url=target_url, referer=referer)
        self.site_headers = dict(site_headers)
        if domain_config is not None:
            self.domain_config = dict(domain_config)
        return dict(site_headers), dict(domain_config) if isinstance(domain_config, dict) else None

    def _build_runtime_headers(self, target_url: str, referer: Optional[str] = None) -> Dict[str, str]:
        site_headers = self.site_headers
        if target_url or referer or not site_headers:
            site_headers, _ = self._resolve_runtime_proxy_config(target_url=target_url, referer=referer)

        custom_headers: Dict[str, str] = {}

        cookie_header = filter_cookies_to_query_string(target_url)
        if cookie_header:
            custom_headers['Cookie'] = cookie_header

        return HeaderBuilder.build_headers(self.request, site_headers, custom_headers)

    def _rewrite_playlist(self, url: str, content: bytes, referer: Optional[str] = None) -> Optional[Dict[str, Any]]:
        runtime_gateway = self._runtime_gateway or get_runtime_gateway()
        route = runtime_gateway.resolve_route('rewrite_proxy_playlist', domain=self.domain)
        if route is None:
            return None

        response = runtime_gateway.invoke(
            'rewrite_proxy_playlist',
            domain=self.domain,
            payload={
                'url': url,
                'content': content.decode('utf-8', errors='ignore'),
                'referer': referer,
            },
        )
        if not response.ok or not isinstance(response.data, dict):
            return None
        return dict(response.data)

    async def _stream_response(self, response: Any, chunk_size: int) -> AsyncIterator[bytes]:
        try:
            async for chunk in UpstreamResponseAdapter.iter_bytes(response, chunk_size):
                if chunk:
                    yield chunk
        except (OSError, ValueError, TypeError) as e:
            logger.error(f"Error during streaming: {e}")
            raise
        finally:
            await UpstreamResponseAdapter.close(response)

    @asynccontextmanager
    async def _get_http_client(self):
        client = await self._connection_manager.get_client(self.domain, self.domain_config)
        try:
            yield client
        except (OSError, ValueError, TypeError) as e:
            logger.error(f"Error in HTTP client context: {e}")
            if not isinstance(e, ProxyException):
                await self._connection_manager.close_client(self.domain)
            raise

    async def handle_stream(self, url: str, **kwargs) -> StreamingResponse:
        try:
            referer = kwargs.get('referer')
            headers = self._build_runtime_headers(url, referer)
            explicit_chunk_size = kwargs.get('chunk_size')
            effective_chunk_size = explicit_chunk_size
            if effective_chunk_size is None:
                effective_chunk_size = int((self.domain_config or {}).get('chunk_size') or ProxyRequest.chunk_size)

            proxy_request = ProxyRequest(
                url=url,
                timeout=kwargs.get('timeout', 120.0),
                max_retries=kwargs.get('max_retries', 3),
                chunk_size=effective_chunk_size,
                headers=kwargs.get('headers', {}),
                follow_redirects=kwargs.get('follow_redirects', True),
            )

            retry_strategy = RetryStrategy(max_retries=proxy_request.max_retries)
            requester = HttpRequester(self.domain, retry_strategy)
            if proxy_request.headers:
                headers.update(proxy_request.headers)

            async with self._get_http_client() as client:
                response = await requester.execute_request(
                    client,
                    proxy_request,
                    headers,
                    self.domain_config,
                    stream=True,
                )
                content_type = response.headers.get('content-type', '')
                path_lower = urlparse(url).path.lower()
                if path_lower.endswith('.m3u8') or 'application/vnd.apple.mpegurl' in content_type.lower():
                    playlist_content = await UpstreamResponseAdapter.read(response)
                    await UpstreamResponseAdapter.close(response)

                    rewritten = self._rewrite_playlist(url, playlist_content, referer=referer)
                    if rewritten is not None:
                        body = str(rewritten.get('content') or '').encode('utf-8')
                        return StreamingResponse(
                            iter([body]),
                            status_code=response.status_code,
                            headers=dict(rewritten.get('headers') or {}),
                            media_type=str(rewritten.get('media_type') or content_type or 'application/vnd.apple.mpegurl'),
                        )

                    response_headers = ResponseBuilder.build_response_headers(response)
                    return StreamingResponse(
                        iter([playlist_content]),
                        status_code=response.status_code,
                        headers=response_headers,
                        media_type=content_type or 'application/vnd.apple.mpegurl',
                    )

                response_headers = ResponseBuilder.build_response_headers(response)
                stream = self._stream_response(response, proxy_request.chunk_size)

                return StreamingResponse(
                    stream,
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=content_type or 'application/octet-stream',
                )

        except ProxyException:
            raise
        except Exception as e:  # API handler boundary — wrap as ProxyException
            logger.error(f"Unexpected error in handle_stream: {e}", exc_info=True)
            raise ProxyException(f"Internal proxy error: {str(e)}", self.domain, 500)


