import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from core.streaming.proxy import VideoProxy


class _FakeResponse:
    def __init__(self, *, content: bytes, content_type: str = 'application/vnd.apple.mpegurl', status_code: int = 200):
        self.content = content
        self.status_code = status_code
        self.headers = {
            'content-type': content_type,
            'content-length': str(len(content)),
        }

    async def aiter_bytes(self, chunk_size):
        yield self.content


def _read_stream(response) -> bytes:
    async def _consume():
        chunks = []
        async for chunk in response.body_iterator:
            chunks.append(chunk)
        return b''.join(chunks)

    return asyncio.run(_consume())


def test_video_proxy_reads_runtime_proxy_config(monkeypatch):
    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='proxy-config-1',
                ok=True,
                data={
                    'site_headers': {
                        'User-Agent': 'Runtime UA',
                        'Referer': 'https://www.youtube.com',
                    },
                    'domain_configs': [{
                        'domain': 'youtube.com',
                        'connect_timeout': 10.0,
                        'read_timeout': 20.0,
                        'max_retries': 3,
                        'chunk_size': 8192,
                        'max_connections': 5,
                        'keepalive_expiry': 30.0,
                        'enable_http2': True,
                    }],
                },
            )

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')

    assert calls == [{
        'capability': 'resolve_proxy_config',
        'payload': {'domain': 'youtube.com'},
        'site_name': None,
        'domain': 'youtube.com',
        'timeout_ms': None,
    }]
    assert proxy.site_headers['User-Agent'] == 'Runtime UA'
    assert proxy.domain_config['domain'] == 'youtube.com'


def test_video_proxy_rewrites_playlist_via_runtime_capability(monkeypatch):
    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
                            'Referer': 'https://javdb.com',
                        },
                        'domain_configs': [{
                            'domain': 'javdb.com',
                            'connect_timeout': 10.0,
                            'read_timeout': 20.0,
                            'max_retries': 3,
                            'chunk_size': 8192,
                            'max_connections': 5,
                            'keepalive_expiry': 30.0,
                            'enable_http2': True,
                        }],
                    },
                )
            if capability == 'rewrite_proxy_playlist':
                return PluginInvokeResponse(
                    request_id='playlist-1',
                    ok=True,
                    data={
                        'content': '#EXTM3U\n/api/video/proxy?domain=javdb.com&url=https%3A%2F%2Fsurrit.com%2Fseg.ts\n',
                        'media_type': 'application/vnd.apple.mpegurl',
                        'headers': {'Cache-Control': 'no-cache'},
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            if capability == 'rewrite_proxy_playlist':
                return SimpleNamespace(plugin_id='javdb')
            return None

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    async def _fake_execute_request(self, client, proxy_request, headers, domain_config=None):
        return _FakeResponse(content=b'#EXTM3U\nseg.ts\n')

    @asynccontextmanager
    async def _fake_client_context():
        yield object()

    monkeypatch.setattr('core.streaming.proxy.HttpRequester.execute_request', _fake_execute_request)

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(
        proxy.handle_stream(
            'https://surrit.com/example/video.m3u8',
            referer='https://missav.ai/en/example-video',
        )
    )

    assert _read_stream(response).decode('utf-8').startswith('#EXTM3U')
    assert response.headers['cache-control'] == 'no-cache'


def test_video_proxy_uses_cloudflare_bypass_for_configured_domains(monkeypatch):
    bypass_calls = []

    class _BypassClient:
        def mirror(self, url, headers=None):
            bypass_calls.append({
                'url': url,
                'headers': dict(headers or {}),
            })
            return _FakeResponse(content=b'#EXTM3U\nseg.ts\n')

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
                            'Referer': 'https://javdb.com/',
                        },
                        'domain_configs': [{
                            'domain': 'javdb.com',
                            'connect_timeout': 10.0,
                            'read_timeout': 20.0,
                            'max_retries': 0,
                            'chunk_size': 8192,
                            'max_connections': 5,
                            'keepalive_expiry': 30.0,
                            'enable_http2': True,
                            'bypass_mode': 'mirror',
                        }],
                    },
                )
            if capability == 'rewrite_proxy_playlist':
                return PluginInvokeResponse(
                    request_id='playlist-1',
                    ok=True,
                    data={
                        'content': '#EXTM3U\n/api/video/proxy?domain=javdb.com&url=https%3A%2F%2Fsurrit.com%2Fseg.ts\n',
                        'media_type': 'application/vnd.apple.mpegurl',
                        'headers': {'Cache-Control': 'no-cache'},
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            if capability == 'rewrite_proxy_playlist':
                return SimpleNamespace(plugin_id='javdb')
            return None

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr('core.streaming.proxy.get_cloudflare_bypass_client', lambda: _BypassClient())

    @asynccontextmanager
    async def _fake_client_context():
        yield object()

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(
        proxy.handle_stream(
            'https://surrit.com/example/video.m3u8',
            referer='https://missav.ai/en/example-video',
        )
    )

    assert bypass_calls == [{
        'url': 'https://surrit.com/example/video.m3u8',
        'headers': {
            'User-Agent': 'Runtime UA',
            'Referer': 'https://missav.ai/en/example-video',
            'Origin': 'https://missav.ai',
        },
    }]
    assert _read_stream(response).decode('utf-8').startswith('#EXTM3U')
