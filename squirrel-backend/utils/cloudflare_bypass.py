import logging
from typing import Callable, Optional
from urllib.parse import urlparse

import httpx

from core.config import settings

logger = logging.getLogger(__name__)


class CloudflareMirrorClient:
    def __init__(self, service_url: str, timeout: int = 120):
        if not service_url:
            raise ValueError("service_url 不能为空")
        self.service_url = service_url.rstrip('/')
        self.timeout = timeout
        self._client_factory: Callable[[], httpx.AsyncClient] = lambda: httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
        )

    @staticmethod
    async def _close_client(client) -> None:
        close = getattr(client, 'aclose', None)
        if callable(close):
            await close()

    async def _bind_streaming_response(self, response, client):
        original_aclose = getattr(response, 'aclose', None)
        close = getattr(response, 'close', None)

        async def close_with_client():
            try:
                if callable(original_aclose):
                    await original_aclose()
                elif callable(close):
                    close()
            finally:
                await self._close_client(client)

        response.aclose = close_with_client
        return response

    async def _send(
        self,
        method: str,
        url: str,
        *,
        params: Optional[dict] = None,
        headers: Optional[dict] = None,
        stream: bool = False,
    ):
        client = self._client_factory()
        try:
            request = client.build_request(
                method,
                url,
                params=params,
                headers=headers.copy() if headers else None,
            )
            response = await client.send(
                request,
                stream=stream,
                follow_redirects=True,
            )
        except Exception:
            await self._close_client(client)
            raise

        if stream:
            return await self._bind_streaming_response(response, client)

        await self._close_client(client)
        return response

    async def html(
        self,
        url: str,
        headers: Optional[dict] = None,
        stream: bool = False,
    ):
        return await self._send(
            'GET',
            f"{self.service_url}/html",
            params={"url": url},
            headers=headers,
            stream=stream,
        )

    async def mirror(
        self,
        url: str,
        headers: Optional[dict] = None,
        stream: bool = False,
    ):
        request_headers = headers.copy() if headers else {}
        parsed_url = urlparse(url)
        path = parsed_url.path.lstrip("/")

        host = parsed_url.netloc
        host = host.split(":")[0]

        service_url = f"{self.service_url}/{path}"
        if parsed_url.query:
            service_url = f"{service_url}?{parsed_url.query}"

        headers = {
            "x-hostname": host,
        }
        headers.update(request_headers)

        return await self._send(
            'GET',
            service_url,
            headers=headers,
            stream=stream,
        )


    async def clear_cache(self):
        return await self._send(
            'POST',
            f"{self.service_url}/cache/clear",
        )

    async def health(self):
        return await self._send(
            'GET',
            f'{self.service_url}/health',
        )


_default_client: Optional[CloudflareMirrorClient] = None


def get_default_client() -> CloudflareMirrorClient:
    global _default_client
    if _default_client is None:
        service_url = settings.CLOUDFLARE_BYPASS_SERVICE_URL
        if not service_url:
            raise ValueError("配置项 CLOUDFLARE_BYPASS_SERVICE_URL 未设置")
        _default_client = CloudflareMirrorClient(service_url)
    return _default_client


