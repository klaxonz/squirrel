import asyncio
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'squirrel-plugins' / 'javdb' / 'src'))

from squirrel_javdb.handler import JavdbHandler
from squirrel_javdb.proxy import JavdbProxy
import squirrel_javdb.proxy as javdb_proxy_module


def _read_stream(response) -> bytes:
    async def _consume() -> bytes:
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        return b''.join(chunks)

    return asyncio.run(_consume())


def test_javdb_handler_builds_proxy_url_with_upstream_referer():
    handler = JavdbHandler()

    proxy_url = handler._build_proxy_url(
        'https://surrit.com/example/playlist/video.m3u8',
        'https://missav.ai/en/example-video',
    )

    parsed = urlparse(proxy_url)
    query = parse_qs(parsed.query)

    assert parsed.path == '/api/video/proxy'
    assert query['domain'] == ['javdb.com']
    assert query['url'] == ['https://surrit.com/example/playlist/video.m3u8']
    assert query['referer'] == ['https://missav.ai/en/example-video']


def test_javdb_proxy_builds_upstream_headers_from_referer(monkeypatch):
    monkeypatch.setattr(
        javdb_proxy_module,
        'build_runtime_proxy_config',
        lambda domain=None: {
            'site_headers': {
                'User-Agent': 'Base UA',
                'Referer': 'https://javdb.com/',
            },
            'domain_configs': [],
        },
    )

    proxy = JavdbProxy()
    proxy._request = SimpleNamespace(headers={})

    headers = proxy._build_upstream_headers('https://missav.ai/en/example-video')

    assert headers['User-Agent'] == 'Base UA'
    assert headers['Referer'] == 'https://missav.ai/en/example-video'
    assert headers['Origin'] == 'https://missav.ai'


def test_javdb_proxy_rewrites_m3u8_entries_with_referer():
    proxy = JavdbProxy()

    response = asyncio.run(
        proxy.handle_m3u8(
            'https://surrit.com/example/1080p/video.m3u8',
            b'#EXTM3U\nsegment-001.ts\n',
            referer='https://missav.ai/en/example-video',
        )
    )

    content = _read_stream(response).decode()
    parsed = urlparse(content.strip().splitlines()[-1])
    query = parse_qs(parsed.query)

    assert parsed.path == '/api/video/proxy'
    assert query['url'] == ['https://surrit.com/example/1080p/segment-001.ts']
    assert query['referer'] == ['https://missav.ai/en/example-video']
