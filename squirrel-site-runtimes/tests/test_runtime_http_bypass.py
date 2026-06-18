from __future__ import annotations

import sys
import unittest
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'shared'))

from crawl import http


@dataclass
class _FakeResponse:
    text: str


class _AsyncBypassClient:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict | None]] = []

    async def html(self, url: str, headers: dict | None = None):
        self.calls.append(('html', url, headers))
        return _FakeResponse(text='ok-html')

    async def mirror(self, url: str, headers: dict | None = None):
        self.calls.append(('mirror', url, headers))
        return _FakeResponse(text='ok-mirror')


class HttpBypassCompatibilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self._original_client = http._cloudflare_bypass_client

    def tearDown(self) -> None:
        http._cloudflare_bypass_client = self._original_client

    def test_request_without_limit_awaits_async_cloudflare_html_client(self):
        client = _AsyncBypassClient()
        http.configure_cloudflare_bypass_client(client)

        response = http.request_without_limit(
            'GET',
            'https://example.com/page',
            bypass_mode='html',
            headers={'User-Agent': 'pytest'},
        )

        self.assertEqual(response.text, 'ok-html')
        self.assertEqual(client.calls, [('html', 'https://example.com/page', {'User-Agent': 'pytest'})])

    def test_request_without_limit_awaits_async_cloudflare_mirror_client(self):
        client = _AsyncBypassClient()
        http.configure_cloudflare_bypass_client(client)

        response = http.request_without_limit(
            'GET',
            'https://example.com/video.m3u8',
            bypass_mode='mirror',
        )

        self.assertEqual(response.text, 'ok-mirror')
        self.assertEqual(client.calls, [('mirror', 'https://example.com/video.m3u8', None)])


if __name__ == '__main__':
    unittest.main()
