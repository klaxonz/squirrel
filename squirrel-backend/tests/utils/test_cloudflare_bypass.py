import asyncio
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils.cloudflare_bypass import CloudflareMirrorClient


class _FakeAsyncHttpxClient:
    def __init__(self):
        self.requests = []

    def build_request(self, method, url, params=None, headers=None):
        request = {
            'method': method,
            'url': url,
            'params': params,
            'headers': dict(headers or {}),
        }
        self.requests.append(request)
        return request

    async def send(self, request, stream=False, follow_redirects=None):
        request['stream'] = stream
        request['follow_redirects'] = follow_redirects
        return request


def test_cloudflare_mirror_client_preserves_query_string_for_mirror_requests():
    client = CloudflareMirrorClient('http://127.0.0.1:8003')
    fake_httpx_client = _FakeAsyncHttpxClient()
    client._client = fake_httpx_client

    response = asyncio.run(
        client.mirror(
            'https://surrit.com/example/video.m3u8?token=abc123&expires=999',
            headers={'Referer': 'https://missav.ai/adn-757'},
            stream=True,
        )
    )

    assert response == {
        'method': 'GET',
        'url': 'http://127.0.0.1:8003/example/video.m3u8?token=abc123&expires=999',
        'params': None,
        'headers': {
            'x-hostname': 'surrit.com',
            'Referer': 'https://missav.ai/adn-757',
        },
        'stream': True,
        'follow_redirects': True,
    }


def test_cloudflare_mirror_client_uses_health_endpoint():
    client = CloudflareMirrorClient('http://127.0.0.1:8003')
    fake_httpx_client = _FakeAsyncHttpxClient()
    client._client = fake_httpx_client

    response = asyncio.run(client.health())

    assert response == {
        'method': 'GET',
        'url': 'http://127.0.0.1:8003/health',
        'params': None,
        'headers': {},
        'stream': False,
        'follow_redirects': True,
    }
