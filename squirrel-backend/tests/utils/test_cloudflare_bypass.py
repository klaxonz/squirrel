import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.site_catalog.cloudflare_bypass import CloudflareMirrorClient


class _FakeAsyncHttpxClient:
    def __init__(self):
        self.requests = []

    def build_request(self, method, url, params=None, headers=None):
        request = {
            "method": method,
            "url": url,
            "params": params,
            "headers": dict(headers or {}),
        }
        self.requests.append(request)
        return request

    async def send(self, request, stream=False, follow_redirects=None):
        request["stream"] = stream
        request["follow_redirects"] = follow_redirects
        return request


class _LoopBoundAsyncHttpxClient:
    def __init__(self):
        self.requests = []
        self._loop = None

    def build_request(self, method, url, params=None, headers=None):
        request = {
            "method": method,
            "url": url,
            "params": params,
            "headers": dict(headers or {}),
        }
        self.requests.append(request)
        return request

    async def send(self, request, stream=False, follow_redirects=None):
        current_loop = asyncio.get_running_loop()
        if self._loop is None:
            self._loop = current_loop
        elif self._loop is not current_loop:
            raise RuntimeError("client reused across event loops")
        request["stream"] = stream
        request["follow_redirects"] = follow_redirects
        return request

    async def aclose(self):
        return None


class _FakeStreamingResponse:
    def __init__(self):
        self.closed = False

    async def aclose(self):
        self.closed = True


class _StreamingAsyncHttpxClient(_FakeAsyncHttpxClient):
    def __init__(self, response):
        super().__init__()
        self.response = response
        self.closed = False

    async def send(self, request, stream=False, follow_redirects=None):
        request["stream"] = stream
        request["follow_redirects"] = follow_redirects
        return self.response

    async def aclose(self):
        self.closed = True


def test_cloudflare_mirror_client_preserves_query_string_for_mirror_requests():
    client = CloudflareMirrorClient("http://127.0.0.1:8003")
    fake_httpx_client = _FakeAsyncHttpxClient()
    client._client_factory = lambda: fake_httpx_client

    response = asyncio.run(
        client.mirror(
            "https://surrit.com/example/video.m3u8?token=abc123&expires=999",
            headers={"Referer": "https://missav.ai/adn-757"},
            stream=False,
        ),
    )

    assert response == {
        "method": "GET",
        "url": "http://127.0.0.1:8003/example/video.m3u8?token=abc123&expires=999",
        "params": None,
        "headers": {
            "x-hostname": "surrit.com",
            "Referer": "https://missav.ai/adn-757",
        },
        "stream": False,
        "follow_redirects": True,
    }


def test_cloudflare_mirror_client_uses_health_endpoint():
    client = CloudflareMirrorClient("http://127.0.0.1:8003")
    fake_httpx_client = _FakeAsyncHttpxClient()
    client._client_factory = lambda: fake_httpx_client

    response = asyncio.run(client.health())

    assert response == {
        "method": "GET",
        "url": "http://127.0.0.1:8003/health",
        "params": None,
        "headers": {},
        "stream": False,
        "follow_redirects": True,
    }


def test_cloudflare_mirror_client_supports_repeated_sync_bridge_calls_across_event_loops():
    client = CloudflareMirrorClient("http://127.0.0.1:8003")
    created_clients = []

    def factory():
        fake_client = _LoopBoundAsyncHttpxClient()
        created_clients.append(fake_client)
        return fake_client

    client._client_factory = factory

    first = asyncio.run(client.html("https://example.com/first"))
    second = asyncio.run(client.html("https://example.com/second"))

    assert first["url"] == "http://127.0.0.1:8003/html"
    assert second["url"] == "http://127.0.0.1:8003/html"
    assert len(created_clients) == 2


def test_cloudflare_mirror_client_keeps_streaming_client_open_until_response_close():
    client = CloudflareMirrorClient("http://127.0.0.1:8003")
    streaming_response = _FakeStreamingResponse()
    created_clients = []

    def factory():
        fake_client = _StreamingAsyncHttpxClient(streaming_response)
        created_clients.append(fake_client)
        return fake_client

    client._client_factory = factory

    response = asyncio.run(
        client.mirror(
            "https://surrit.com/example/video.m3u8?token=abc123",
            stream=True,
        ),
    )

    assert response is streaming_response
    assert len(created_clients) == 1
    assert created_clients[0].closed is False
    assert streaming_response.closed is False

    asyncio.run(response.aclose())

    assert streaming_response.closed is True
    assert created_clients[0].closed is True
