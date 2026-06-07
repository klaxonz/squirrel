from __future__ import annotations

import importlib
import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlencode, urljoin, urlparse

REPO_ROOT = Path(__file__).resolve().parents[2]

PROXY_MODULES = {
    'javdb': {
        'package_root': REPO_ROOT / 'squirrel-site-runtimes' / 'javdb' / 'src',
        'module': 'squirrel_javdb.proxy',
        'domain': 'javdb.com',
    },
    'pornhub': {
        'package_root': REPO_ROOT / 'squirrel-site-runtimes' / 'pornhub' / 'src',
        'module': 'squirrel_pornhub.proxy',
        'domain': 'pornhub.com',
    },
    'youporn': {
        'package_root': REPO_ROOT / 'squirrel-site-runtimes' / 'youporn' / 'src',
        'module': 'squirrel_youporn.proxy',
        'domain': 'youporn.com',
    },
    'youtube': {
        'package_root': REPO_ROOT / 'squirrel-site-runtimes' / 'youtube' / 'src',
        'module': 'squirrel_youtube.proxy',
        'domain': 'youtube.com',
    },
}


@contextmanager
def _import_paths(*paths: Path):
    original_sys_path = list(sys.path)
    try:
        for path in reversed(paths):
            sys.path.insert(0, str(path))
        yield
    finally:
        sys.path[:] = original_sys_path


@contextmanager
def _stub_proxy_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'crawl',
            'httpx',
            'fastapi',
            'starlette',
            'starlette.responses',
        )
    }

    crawl_module = types.ModuleType('crawl')
    crawl_module.build_proxy_config_values = lambda _site, defaults: dict(defaults)

    def build_runtime_proxy_config(*, site_slug, site_domain, default_site_headers, default_proxy_config, domain=None):
        return {
            'site_headers': dict(default_site_headers),
            'domain_configs': [{
                'domain': domain or site_domain,
                'connect_timeout': float(default_proxy_config['connect_timeout']),
                'read_timeout': float(default_proxy_config['read_timeout']),
                'max_retries': int(default_proxy_config['max_retries']),
                'chunk_size': int(default_proxy_config['chunk_size']),
                'max_connections': int(default_proxy_config['max_connections']),
                'keepalive_expiry': float(default_proxy_config['keepalive_expiry']),
                'enable_http2': bool(default_proxy_config['enable_http2']),
            }],
        }

    def rewrite_playlist_for_proxy(*, url, content, site_domain, referer=None, extensions):
        content_text = content.decode(errors='ignore') if isinstance(content, (bytes, bytearray)) else str(content)
        base_url = url.rsplit('/', 1)[0]
        rewritten_lines = []
        suffixes = tuple(f'.{ext}' for ext in extensions)

        def build_proxy_url(path):
            full_url = path if path.startswith('http') else urljoin(base_url + '/', path)
            params = {'domain': site_domain, 'url': full_url}
            if referer:
                params['referer'] = referer
            return f'/api/video/proxy?{urlencode(params)}'

        for line in content_text.splitlines():
            if 'URI="' in line:
                prefix, rest = line.split('URI="', 1)
                original, suffix = rest.split('"', 1)
                if any(ext in original for ext in suffixes):
                    rewritten_lines.append(f'{prefix}URI="{build_proxy_url(original)}"{suffix}')
                    continue

            stripped = line.strip()
            if stripped and not stripped.startswith('#') and stripped.endswith(suffixes):
                rewritten_lines.append(build_proxy_url(stripped))
            else:
                rewritten_lines.append(line)

        rewritten = '\n'.join(rewritten_lines)
        if content_text.endswith('\n'):
            rewritten += '\n'
        return {
            'content': rewritten,
            'media_type': 'application/vnd.apple.mpegurl',
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Cache-Control': 'no-cache',
            },
        }

    crawl_module.build_runtime_proxy_config = build_runtime_proxy_config
    crawl_module.rewrite_playlist_for_proxy = rewrite_playlist_for_proxy
    crawl_module.safe_cookie_header_value = lambda _target: ''

    httpx_module = types.ModuleType('httpx')

    class Timeout:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class Limits:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class AsyncClient:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class HTTPError(Exception):
        pass

    class HTTPStatusError(HTTPError):
        def __init__(self, *args, response=None, **kwargs):
            super().__init__(*args)
            self.response = response

    httpx_module.Timeout = Timeout
    httpx_module.Limits = Limits
    httpx_module.AsyncClient = AsyncClient
    httpx_module.HTTPError = HTTPError
    httpx_module.HTTPStatusError = HTTPStatusError

    fastapi_module = types.ModuleType('fastapi')

    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    fastapi_module.HTTPException = HTTPException

    starlette_module = types.ModuleType('starlette')
    responses_module = types.ModuleType('starlette.responses')

    class StreamingResponse:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    responses_module.StreamingResponse = StreamingResponse
    starlette_module.responses = responses_module

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['httpx'] = httpx_module
        sys.modules['fastapi'] = fastapi_module
        sys.modules['starlette'] = starlette_module
        sys.modules['starlette.responses'] = responses_module
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_proxy_module(name: str):
    spec = PROXY_MODULES[name]
    with _stub_proxy_dependencies(), _import_paths(spec['package_root']):
        module_name = f'_proxy_test_{name}'
        sys.modules.pop(module_name, None)
        module_path = spec['package_root'] / spec['module'].replace('.', '/')
        file_path = module_path.with_suffix('.py')
        module_spec = importlib.util.spec_from_file_location(module_name, file_path)
        module = importlib.util.module_from_spec(module_spec)
        assert module_spec is not None and module_spec.loader is not None
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        return module


def _extract_proxy_url(line: str) -> str:
    parsed = urlparse(line)
    params = parse_qs(parsed.query)
    return unquote(params['url'][0])


class ProxyPlaylistRewriteTests(unittest.TestCase):
    def test_youtube_proxy_runtime_config_can_customize_headers_for_googlevideo_requests(self):
        module = _load_proxy_module('youtube')

        config = module.build_runtime_proxy_config({
            'domain': 'youtube.com',
            'target_url': 'https://rr3---sn-a5mekn6z.googlevideo.com/videoplayback?c=MWEB&source=youtube',
            'referer': 'https://www.youtube.com/watch?v=lUQ2NKkCW_Q',
        })

        self.assertEqual(config['site_headers']['Referer'], 'https://m.youtube.com/watch?v=lUQ2NKkCW_Q')
        self.assertEqual(config['site_headers']['Origin'], 'https://m.youtube.com')
        self.assertNotEqual(
            config['site_headers']['User-Agent'],
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        )

    def test_map_uri_attributes_are_rewritten_for_all_plugins(self):
        playlist = '#EXTM3U\n#EXT-X-MAP:URI="init.mp4"\nsegment-1.ts\n'

        for plugin_name, spec in PROXY_MODULES.items():
            with self.subTest(plugin=plugin_name):
                module = _load_proxy_module(plugin_name)
                rewritten = module.rewrite_proxy_playlist(
                    f'https://cdn.{spec["domain"]}/path/master.m3u8',
                    playlist,
                    referer=f'https://www.{spec["domain"]}/watch',
                )['content']
                self.assertIn('URI="/api/video/proxy?', rewritten)
                self.assertIn('/api/video/proxy?', rewritten.splitlines()[2])
                self.assertEqual(
                    _extract_proxy_url(rewritten.splitlines()[1].split('"')[1]),
                    f'https://cdn.{spec["domain"]}/path/init.mp4',
                )

    def test_comment_lines_with_media_names_are_not_rewritten(self):
        playlist = '#EXTM3U\n# comment about teaser.ts\nsegment-1.ts\n'

        for plugin_name, spec in PROXY_MODULES.items():
            with self.subTest(plugin=plugin_name):
                module = _load_proxy_module(plugin_name)
                rewritten = module.rewrite_proxy_playlist(
                    f'https://cdn.{spec["domain"]}/path/master.m3u8',
                    playlist,
                )['content']
                self.assertEqual(rewritten.splitlines()[1], '# comment about teaser.ts')
                self.assertIn('/api/video/proxy?', rewritten.splitlines()[2])


if __name__ == '__main__':
    unittest.main()
