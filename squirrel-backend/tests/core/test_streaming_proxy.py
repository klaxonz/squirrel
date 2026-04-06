import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from core.exceptions.proxy_exceptions import ProxyConfigurationException
from core.exceptions.proxy_exceptions import ProxyNetworkException
from core.streaming.proxy import VideoProxy


@pytest.fixture(autouse=True)
def _reset_proxy_runtime_cache(monkeypatch):
    monkeypatch.setattr(VideoProxy, '_runtime_config_cache', {}, raising=False)


class _FakeResponse:
    def __init__(self, *, content: bytes, content_type: str = 'application/vnd.apple.mpegurl', status_code: int = 200):
        self.content = content
        self.status_code = status_code
        self.headers = {
            'content-type': content_type,
            'content-length': str(len(content)),
        }
        self.closed = False

    async def aiter_bytes(self, chunk_size):
        yield self.content

    async def aread(self):
        return self.content

    async def aclose(self):
        self.closed = True


class _RequestsLikeResponse:
    def __init__(self, *, content: bytes, content_type: str = 'application/vnd.apple.mpegurl', status_code: int = 200):
        self.content = content
        self.status_code = status_code
        self.headers = {
            'content-type': content_type,
            'content-length': str(len(content)),
        }
        self.text = content.decode('utf-8', errors='ignore')
        self.closed = False

    def iter_content(self, chunk_size=1):
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index + chunk_size]

    def close(self):
        self.closed = True


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
    headers = proxy._build_runtime_headers('https://cdn.example.com/segment-001.ts')

    assert calls == [{
        'capability': 'resolve_proxy_config',
        'payload': {
            'domain': 'youtube.com',
            'target_url': 'https://cdn.example.com/segment-001.ts',
        },
        'site_name': None,
        'domain': 'youtube.com',
        'timeout_ms': None,
    }]
    assert headers['User-Agent'] == 'Runtime UA'
    assert proxy.site_headers['User-Agent'] == 'Runtime UA'
    assert proxy.domain_config['domain'] == 'youtube.com'


def test_video_proxy_caches_runtime_proxy_config_for_identical_requests(monkeypatch):
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
                        'Referer': 'https://m.youtube.com/watch?v=demo',
                    },
                    'domain_configs': [{
                        'domain': 'youtube.com',
                        'connect_timeout': 10.0,
                        'read_timeout': 20.0,
                        'max_retries': 3,
                        'chunk_size': 65536,
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
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')
    first = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')
    second = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')

    first_headers = first._build_runtime_headers(
        'https://rr3---sn-a5mekn6z.googlevideo.com/videoplayback?c=MWEB&source=youtube',
        referer='https://www.youtube.com/watch?v=demo',
    )
    second_headers = second._build_runtime_headers(
        'https://rr3---sn-a5mekn6z.googlevideo.com/videoplayback?c=MWEB&source=youtube',
        referer='https://www.youtube.com/watch?v=demo',
    )

    assert first_headers['User-Agent'] == 'Runtime UA'
    assert second_headers['Referer'] == 'https://m.youtube.com/watch?v=demo'
    assert calls == [{
        'capability': 'resolve_proxy_config',
        'payload': {
            'domain': 'youtube.com',
            'target_url': 'https://rr3---sn-a5mekn6z.googlevideo.com/videoplayback?c=MWEB&source=youtube',
            'referer': 'https://www.youtube.com/watch?v=demo',
        },
        'site_name': None,
        'domain': 'youtube.com',
        'timeout_ms': None,
    }]


def test_video_proxy_raises_when_runtime_proxy_config_is_missing(monkeypatch):
    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            return PluginInvokeResponse(
                request_id='proxy-config-1',
                ok=False,
                error={'code': 'missing'},
            )

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')

    with pytest.raises(ProxyConfigurationException):
        proxy._build_runtime_headers('https://cdn.example.com/segment-001.ts')


def test_video_proxy_builds_cookie_header_from_target_url(monkeypatch):
    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
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
            raise AssertionError(f'unexpected capability: {capability}')

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr(
        'core.streaming.proxy.filter_cookies_to_query_string',
        lambda target_url: 'SID=test-cookie' if 'googlevideo.com' in target_url else '',
    )

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')

    headers = proxy._build_runtime_headers('https://rr5---sn-a5mekndl.googlevideo.com/videoplayback')

    assert headers == {
        'User-Agent': 'Runtime UA',
        'Cookie': 'SID=test-cookie',
    }


def test_video_proxy_uses_runtime_capability_headers_for_target_specific_youtube_requests(monkeypatch):
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
            if capability == 'resolve_proxy_config':
                dynamic_target = (payload or {}).get('target_url')
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Plugin MWEB UA' if dynamic_target else 'Runtime UA',
                            'Referer': 'https://m.youtube.com/watch?v=lUQ2NKkCW_Q' if dynamic_target else 'https://www.youtube.com',
                            'Origin': 'https://m.youtube.com' if dynamic_target else 'https://www.youtube.com',
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
            raise AssertionError(f'unexpected capability: {capability}')

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')

    headers = proxy._build_runtime_headers(
        'https://rr3---sn-a5mekn6z.googlevideo.com/videoplayback?c=MWEB&source=youtube',
        referer='https://www.youtube.com/watch?v=lUQ2NKkCW_Q',
    )

    assert calls == [
        {
            'capability': 'resolve_proxy_config',
            'payload': {
                'domain': 'youtube.com',
                'target_url': 'https://rr3---sn-a5mekn6z.googlevideo.com/videoplayback?c=MWEB&source=youtube',
                'referer': 'https://www.youtube.com/watch?v=lUQ2NKkCW_Q',
            },
            'site_name': None,
            'domain': 'youtube.com',
            'timeout_ms': None,
        },
    ]
    assert headers['User-Agent'] == 'Plugin MWEB UA'
    assert headers['Referer'] == 'https://m.youtube.com/watch?v=lUQ2NKkCW_Q'
    assert headers['Origin'] == 'https://m.youtube.com'


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

    async def _fake_execute_request(self, client, proxy_request, headers, domain_config=None, stream=False):
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
    client_calls = []
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

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
                referer = (payload or {}).get('referer')
                site_headers = {
                    'User-Agent': 'Runtime UA',
                    'Referer': 'https://javdb.com/',
                }
                if referer:
                    site_headers['Referer'] = referer
                    site_headers['Origin'] = 'https://javdb.com'
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': site_headers,
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

    class _FakeClient:
        def build_request(self, method, url, headers=None, timeout=None):
            client_calls.append({
                'method': method,
                'url': url,
                'headers': dict(headers or {}),
                'timeout': timeout,
            })
            return SimpleNamespace(method=method, url=url, headers=headers, timeout=timeout)

        async def send(self, request, stream=False, follow_redirects=None):
            client_calls.append({
                'stream': stream,
                'follow_redirects': follow_redirects,
            })
            return _FakeResponse(content=b'#EXTM3U\nseg.ts\n')

    @asynccontextmanager
    async def _fake_client_context():
        yield _FakeClient()

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(
        proxy.handle_stream(
            'https://javdb.com/video.m3u8',
            referer='https://javdb.com/v/abc123',
        )
    )

    assert bypass_calls == [{
        'url': 'https://javdb.com/video.m3u8',
        'headers': {
            'User-Agent': 'Runtime UA',
            'Referer': 'https://javdb.com/v/abc123',
            'Origin': 'https://javdb.com',
        },
    }]
    assert client_calls == []
    assert _read_stream(response).decode('utf-8').startswith('#EXTM3U')


def test_video_proxy_accepts_requests_style_playlist_response_from_cloudflare_bypass(monkeypatch):
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

    class _BypassClient:
        def mirror(self, url, headers=None):
            return _RequestsLikeResponse(content=b'#EXTM3U\nseg.ts\n')

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
                            'Referer': 'https://javdb.com/v/abc123',
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
                            'bypass_domains': ['surrit.com'],
                        }],
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    @asynccontextmanager
    async def _fake_client_context():
        yield object()

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr('core.streaming.proxy.get_cloudflare_bypass_client', lambda: _BypassClient())

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(proxy.handle_stream('https://surrit.com/example/video.m3u8'))

    assert _read_stream(response) == b'#EXTM3U\nseg.ts\n'


def test_video_proxy_streams_requests_style_media_segments_from_cloudflare_bypass(monkeypatch):
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')
    bypass_response = _RequestsLikeResponse(content=b'chunk-onechunk-two', content_type='video/mp2t')

    class _BypassClient:
        def mirror(self, url, headers=None):
            return bypass_response

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
                        },
                        'domain_configs': [{
                            'domain': 'javdb.com',
                            'connect_timeout': 10.0,
                            'read_timeout': 20.0,
                            'max_retries': 0,
                            'chunk_size': 5,
                            'max_connections': 5,
                            'keepalive_expiry': 30.0,
                            'enable_http2': True,
                            'bypass_mode': 'mirror',
                            'bypass_domains': ['surrit.com'],
                        }],
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    @asynccontextmanager
    async def _fake_client_context():
        yield object()

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr('core.streaming.proxy.get_cloudflare_bypass_client', lambda: _BypassClient())

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(proxy.handle_stream('https://surrit.com/example/segment-001.ts'))

    assert _read_stream(response) == b'chunk-onechunk-two'
    assert bypass_response.closed is True


def test_video_proxy_accepts_async_cloudflare_bypass_clients(monkeypatch):
    bypass_calls = []
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

    class _BypassClient:
        async def mirror(self, url, headers=None):
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
                            'bypass_domains': ['surrit.com'],
                        }],
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    @asynccontextmanager
    async def _fake_client_context():
        yield object()

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr('core.streaming.proxy.get_cloudflare_bypass_client', lambda: _BypassClient())

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(proxy.handle_stream('https://surrit.com/example/video.m3u8'))

    assert bypass_calls == [{
        'url': 'https://surrit.com/example/video.m3u8',
        'headers': {'User-Agent': 'Runtime UA'},
    }]
    assert _read_stream(response) == b'#EXTM3U\nseg.ts\n'


def test_video_proxy_skips_cloudflare_bypass_for_cross_host_streams(monkeypatch):
    bypass_calls = []
    client_calls = []
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

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
                referer = (payload or {}).get('referer')
                site_headers = {
                    'User-Agent': 'Runtime UA',
                    'Referer': 'https://javdb.com/',
                }
                if referer:
                    site_headers['Referer'] = referer
                    site_headers['Origin'] = 'https://missav.ai'
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': site_headers,
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

    class _FakeClient:
        def build_request(self, method, url, headers=None, timeout=None):
            client_calls.append({
                'method': method,
                'url': url,
                'headers': dict(headers or {}),
                'timeout': timeout,
            })
            return SimpleNamespace(method=method, url=url, headers=headers, timeout=timeout)

        async def send(self, request, stream=False, follow_redirects=None):
            client_calls.append({
                'stream': stream,
                'follow_redirects': follow_redirects,
            })
            return _FakeResponse(content=b'#EXTM3U\nseg.ts\n')

    @asynccontextmanager
    async def _fake_client_context():
        yield _FakeClient()

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='javdb.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(
        proxy.handle_stream(
            'https://surrit.com/example/video.m3u8',
            referer='https://missav.ai/en/example-video',
        )
    )

    assert bypass_calls == []
    assert client_calls == [{
        'method': 'GET',
        'url': 'https://surrit.com/example/video.m3u8',
        'headers': {
            'User-Agent': 'Runtime UA',
            'Referer': 'https://missav.ai/en/example-video',
            'Origin': 'https://missav.ai',
        },
        'timeout': 120.0,
    }, {
        'stream': True,
        'follow_redirects': True,
    }]
    assert _read_stream(response).decode('utf-8').startswith('#EXTM3U')


def test_video_proxy_uses_cloudflare_bypass_for_explicit_cross_host_domains(monkeypatch):
    bypass_calls = []
    client_calls = []
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

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
                referer = (payload or {}).get('referer')
                site_headers = {
                    'User-Agent': 'Runtime UA',
                    'Referer': 'https://javdb.com/',
                }
                if referer:
                    site_headers['Referer'] = referer
                    site_headers['Origin'] = 'https://missav.ai'
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': site_headers,
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
                            'bypass_domains': ['surrit.com'],
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

    class _FakeClient:
        def build_request(self, method, url, headers=None, timeout=None):
            client_calls.append({
                'method': method,
                'url': url,
                'headers': dict(headers or {}),
                'timeout': timeout,
            })
            return SimpleNamespace(method=method, url=url, headers=headers, timeout=timeout)

        async def send(self, request, stream=False, follow_redirects=None):
            client_calls.append({
                'stream': stream,
                'follow_redirects': follow_redirects,
            })
            return _FakeResponse(content=b'#EXTM3U\nseg.ts\n')

    @asynccontextmanager
    async def _fake_client_context():
        yield _FakeClient()

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
    assert client_calls == []
    assert _read_stream(response).decode('utf-8').startswith('#EXTM3U')


def test_video_proxy_keeps_shared_client_open_on_proxy_exception(monkeypatch):
    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {'User-Agent': 'Runtime UA'},
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
            raise AssertionError(f'unexpected capability: {capability}')

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')

    class _FakeConnectionManager:
        def __init__(self):
            self.close_calls = []
            self.client = object()

        async def get_client(self, domain, domain_config):
            return self.client

        async def close_client(self, domain):
            self.close_calls.append(domain)

    fake_manager = _FakeConnectionManager()
    proxy._connection_manager = fake_manager

    async def _run():
        try:
            async with proxy._get_http_client():
                raise ProxyNetworkException('youtube.com', 'HTTP 403')
        except ProxyNetworkException:
            pass

    asyncio.run(_run())

    assert fake_manager.close_calls == []


def test_video_proxy_streams_media_segments_without_prefetching_entire_body(monkeypatch):
    send_calls = []
    streamed_response = _FakeResponse(content=b'chunk-onechunk-two', content_type='video/mp2t')
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
                        },
                        'domain_configs': [{
                            'domain': 'youtube.com',
                            'connect_timeout': 10.0,
                            'read_timeout': 20.0,
                            'max_retries': 0,
                            'chunk_size': 8192,
                            'max_connections': 5,
                            'keepalive_expiry': 30.0,
                            'enable_http2': True,
                        }],
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    class _FakeClient:
        def build_request(self, method, url, headers=None, timeout=None):
            send_calls.append({
                'method': method,
                'url': url,
                'headers': dict(headers or {}),
                'timeout': timeout,
            })
            return SimpleNamespace(method=method, url=url, headers=headers, timeout=timeout)

        async def send(self, request, stream=False, follow_redirects=None):
            send_calls.append({
                'stream': stream,
                'follow_redirects': follow_redirects,
                'request_url': request.url,
            })
            return streamed_response

    @asynccontextmanager
    async def _fake_client_context():
        yield _FakeClient()

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(proxy.handle_stream('https://cdn.example.com/segment-001.ts'))

    assert _read_stream(response) == b'chunk-onechunk-two'
    assert send_calls == [
        {
            'method': 'GET',
            'url': 'https://cdn.example.com/segment-001.ts',
            'headers': {'User-Agent': 'Runtime UA'},
            'timeout': 120.0,
        },
        {
            'stream': True,
            'follow_redirects': True,
            'request_url': 'https://cdn.example.com/segment-001.ts',
        },
    ]
    assert streamed_response.closed is True
def test_video_proxy_uses_runtime_chunk_size_when_not_explicitly_overridden(monkeypatch):
    observed_chunk_sizes = []
    monkeypatch.setattr('core.streaming.proxy.filter_cookies_to_query_string', lambda _url: '')

    class _ChunkAwareResponse(_FakeResponse):
        async def aiter_bytes(self, chunk_size):
            observed_chunk_sizes.append(chunk_size)
            yield self.content

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            if capability == 'resolve_proxy_config':
                return PluginInvokeResponse(
                    request_id='proxy-config-1',
                    ok=True,
                    data={
                        'site_headers': {
                            'User-Agent': 'Runtime UA',
                        },
                        'domain_configs': [{
                            'domain': 'youtube.com',
                            'connect_timeout': 10.0,
                            'read_timeout': 20.0,
                            'max_retries': 0,
                            'chunk_size': 131072,
                            'max_connections': 5,
                            'keepalive_expiry': 30.0,
                            'enable_http2': True,
                        }],
                    },
                )
            raise AssertionError(f'unexpected capability: {capability}')

        def resolve_route(self, capability, site_name=None, domain=None):
            return None

    monkeypatch.setattr(
        'core.streaming.proxy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )

    class _FakeClient:
        def build_request(self, method, url, headers=None, timeout=None):
            return SimpleNamespace(method=method, url=url, headers=headers, timeout=timeout)

        async def send(self, request, stream=False, follow_redirects=None):
            return _ChunkAwareResponse(content=b'chunk-data', content_type='video/mp2t')

    @asynccontextmanager
    async def _fake_client_context():
        yield _FakeClient()

    proxy = VideoProxy(SimpleNamespace(headers={}), domain='youtube.com')
    proxy._get_http_client = _fake_client_context

    response = asyncio.run(proxy.handle_stream('https://cdn.example.com/segment-001.ts'))

    assert _read_stream(response) == b'chunk-data'
    assert observed_chunk_sizes == [131072]
