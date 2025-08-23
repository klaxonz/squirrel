import logging
from typing import Optional
import httpx
from fastapi import Request, HTTPException
from starlette.responses import StreamingResponse
from sites.proxy_config import ProxyConfigFactory
from sites.proxy_registry import ProxyRegistry

logger = logging.getLogger(__name__)


class VideoProxy:
    domain: Optional[str] = None

    def __init__(self, request: Request):
        self.request = request
        self.proxy_config = ProxyConfigFactory.create_proxy_config(self.domain)

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

        upstream_headers = ProxyConfigFactory.create_proxy_config(self.domain).get_site_headers()

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


class ProxyFactory:
    @staticmethod
    def create_proxy(domain: str, request: Request) -> VideoProxy:
        proxy_class = ProxyRegistry.get_proxy_class(domain)
        if proxy_class:
            return proxy_class(request)

        raise ValueError(f"No proxy registered for domain: {domain}")
