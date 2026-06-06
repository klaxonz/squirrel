from pathlib import Path
import importlib.util
import sys
import unittest
import types
from datetime import datetime
from unittest import mock


ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR_PATH = ROOT / 'squirrel-site-runtimes' / 'youporn' / 'src' / 'squirrel_youporn' / 'extractor.py'


def _load_extractor_module():
    originals = {name: sys.modules.get(name) for name in ('crawl',)}

    crawl_module = types.ModuleType('crawl')

    class YoutubeDLExtractorBase:
        def __init__(self, site_name, supported_domains):
            self.site_name = site_name
            self.supported_domains = supported_domains

    class _PluginError(Exception):
        def __init__(self, message, context=None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    class AuthError(_PluginError):
        pass

    class NetworkError(_PluginError):
        pass

    class NotFoundError(_PluginError):
        pass

    class ParseError(_PluginError):
        pass

    crawl_module.YoutubeDLExtractorBase = YoutubeDLExtractorBase
    crawl_module.AuthError = AuthError
    crawl_module.NetworkError = NetworkError
    crawl_module.NotFoundError = NotFoundError
    crawl_module.ParseError = ParseError
    crawl_module.apply_ytdlp_rate_limit = lambda _site, opts: dict(opts)
    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})
    crawl_module.resolve_cookie_file_path = lambda _url: None

    module_name = '_test_squirrel_youporn_extractor'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, EXTRACTOR_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        return module
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


class _FakeYoutubeDL:
    def __init__(self, _opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, _url, download=False):
        return {
            'title': 'Demo',
            'timestamp': 1700000000,
            'duration': 321,
            'thumbnail': 'https://cdn.example/thumb.jpg',
        }


class YouPornExtractorTests(unittest.TestCase):
    def test_youporn_extractor_adds_publish_date_from_timestamp(self):
        youporn_extractor = _load_extractor_module()

        with mock.patch.object(youporn_extractor, 'YoutubeDL', _FakeYoutubeDL):
            extractor = youporn_extractor.YouPornExtractor()
            extractor._build_ytdlp_opts = lambda url, queue_name=None: {}

            info = extractor._extract_with_ytdlp('https://www.youporn.com/watch/123456/demo-video/')

        self.assertEqual(info['title'], 'Demo')
        self.assertEqual(info['duration'], 321)
        self.assertEqual(info['publish_date'], datetime.fromtimestamp(1700000000))

    def test_youporn_extractor_rewrites_expiring_preview_thumbnail_from_page_metadata(self):
        youporn_extractor = _load_extractor_module()

        class _PreviewYoutubeDL(_FakeYoutubeDL):
            def extract_info(self, _url, download=False):
                return {
                    'title': 'Demo',
                    'timestamp': 1700000000,
                    'duration': 321,
                    'webpage_url': 'https://www.youporn.com/watch/123456/demo-video/',
                    'thumbnail': (
                        'https://pix-cdn77.ypncdn.com/c6251/videos/demo.mp4/plain/'
                        'rs:fit:1280:720/vts:620?hash=stale&validto=123'
                    ),
                    'thumbnails': [
                        {
                            'url': (
                                'https://pix-cdn77.ypncdn.com/c6251/videos/demo.mp4/plain/'
                                'rs:fit:1280:720/vts:620?hash=stale&validto=123'
                            ),
                            'id': '0',
                        }
                    ],
                }

        class _FakeHttpResponse:
            status_code = 200
            text = (
                '<meta property="og:image" '
                'content="https://cdn.example.com/thumb.jpg?hash=fresh&amp;validto=456">'
            )

        with mock.patch.object(youporn_extractor, 'YoutubeDL', _PreviewYoutubeDL), mock.patch.object(
            youporn_extractor.httpx,
            'get',
            return_value=_FakeHttpResponse(),
        ):
            extractor = youporn_extractor.YouPornExtractor()
            extractor._build_ytdlp_opts = lambda url, queue_name=None: {}

            info = extractor._extract_with_ytdlp('https://www.youporn.com/watch/123456/demo-video/')

        self.assertEqual(
            info['thumbnail'],
            'https://cdn.example.com/thumb.jpg?hash=fresh&validto=456',
        )
        self.assertEqual(
            info['thumbnails'][0]['url'],
            'https://cdn.example.com/thumb.jpg?hash=fresh&validto=456',
        )


if __name__ == '__main__':
    unittest.main()
