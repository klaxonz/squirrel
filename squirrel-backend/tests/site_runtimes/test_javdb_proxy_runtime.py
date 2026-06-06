import asyncio
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'squirrel-plugins' / 'javdb' / 'src'))

from squirrel_javdb.proxy import JavdbProxy
import squirrel_javdb.proxy as javdb_proxy_module


def _read_stream(response) -> bytes:
    async def _consume() -> bytes:
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        return b''.join(chunks)

    return asyncio.run(_consume())


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


def test_javdb_proxy_config_exposes_cross_host_bypass_domains():
    payload = {
        'domain': 'javdb.com',
        'target_url': 'https://surrit.com/example/video.m3u8',
        'referer': 'https://missav.ai/en/example-video',
    }

    config = javdb_proxy_module.build_runtime_proxy_config(payload)
    domain_config = config['domain_configs'][0]

    assert domain_config['domain'] == 'javdb.com'
    assert domain_config['bypass_domains'] == ['surrit.com']
    assert config['site_headers']['Referer'] == 'https://missav.ai/en/example-video'
    assert config['site_headers']['Origin'] == 'https://missav.ai'


def test_javdb_proxy_config_skips_cross_host_bypass_domains_for_media_segments():
    payload = {
        'domain': 'javdb.com',
        'target_url': 'https://surrit.com/example/1080p/video720.jpeg',
        'referer': 'https://missav.ai/en/example-video',
    }

    config = javdb_proxy_module.build_runtime_proxy_config(payload)
    domain_config = config['domain_configs'][0]

    assert domain_config['domain'] == 'javdb.com'
    assert 'bypass_domains' not in domain_config
    assert config['site_headers']['Referer'] == 'https://missav.ai/en/example-video'
    assert config['site_headers']['Origin'] == 'https://missav.ai'
