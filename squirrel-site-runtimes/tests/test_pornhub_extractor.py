import importlib.util
import re
import sys
import types
from html import unescape
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

ROOT = Path(__file__).resolve().parents[2]
EXTRACTOR_PATH = ROOT / 'squirrel-site-runtimes' / 'pornhub' / 'src' / 'squirrel_pornhub' / 'extractor.py'


def _load_extractor_module():
    originals = {
        name: sys.modules.get(name)
        for name in ('crawl', 'yt_dlp', 'yt_dlp.networking', 'yt_dlp.networking.impersonate')
    }

    import crawl as real_crawl

    crawl_module = types.ModuleType('crawl')
    crawl_module.__dict__.update(real_crawl.__dict__)

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

    class RateLimitError(_PluginError):
        pass

    def build_cookie_header(_url, cookies):
        return '; '.join(f'{key}={value}' for key, value in cookies.items())

    def fetch_page_thumbnail_url(url, _cookie_file, _headers_builder):
        for attempt in range(2):
            response = module.requests.get(url)
            if response.status_code == 200:
                candidates = [
                    unescape(match)
                    for match in re.findall(
                        r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)["\']',
                        response.text,
                        re.I,
                    )
                ]
                return max(candidates, key=_thumbnail_expiry) if candidates else None
            if attempt == 0:
                module.time.sleep(0.8)
        return None

    def normalize_thumbnail(video_info, source_url, fetcher):
        fresh_thumbnail = fetcher(source_url)
        if not fresh_thumbnail:
            return
        video_info['thumbnail'] = fresh_thumbnail
        for item in video_info.get('thumbnails') or []:
            item['url'] = fresh_thumbnail

    crawl_module.YoutubeDLExtractorBase = YoutubeDLExtractorBase
    crawl_module.AuthError = AuthError
    crawl_module.NetworkError = NetworkError
    crawl_module.NotFoundError = NotFoundError
    crawl_module.ParseError = ParseError
    crawl_module.RateLimitError = RateLimitError
    crawl_module.apply_ytdlp_rate_limit = lambda _site, opts: dict(opts)
    crawl_module.build_cookie_header = build_cookie_header
    crawl_module.fetch_page_thumbnail_url = fetch_page_thumbnail_url
    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})
    crawl_module.normalize_thumbnail = normalize_thumbnail
    crawl_module.resolve_cookie_file_path = lambda _url: None

    yt_dlp_module = types.ModuleType('yt_dlp')
    yt_dlp_networking_module = types.ModuleType('yt_dlp.networking')
    yt_dlp_impersonate_module = types.ModuleType('yt_dlp.networking.impersonate')

    class ImpersonateTarget:
        @classmethod
        def from_str(cls, target):
            return cls(target)

        def __init__(self, target):
            self.target = target

        def __str__(self):
            return self.target

    yt_dlp_module.YoutubeDL = object
    yt_dlp_impersonate_module.ImpersonateTarget = ImpersonateTarget

    module_name = '_test_squirrel_pornhub_extractor'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, EXTRACTOR_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['yt_dlp'] = yt_dlp_module
        sys.modules['yt_dlp.networking'] = yt_dlp_networking_module
        sys.modules['yt_dlp.networking.impersonate'] = yt_dlp_impersonate_module
        sys.modules[module_name] = module
        module_spec.loader.exec_module(module)
        module.requests = types.SimpleNamespace(get=lambda *_args, **_kwargs: None)
        module.time = types.SimpleNamespace(sleep=lambda _seconds: None)
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
        raise RuntimeError(
            'ERROR: [PornHub] 698e147975244: Unable to extract encoded url; '
            'please report this issue on https://github.com/yt-dlp/yt-dlp/issues'
        )


class _Http410YoutubeDL:
    def __init__(self, _opts):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def extract_info(self, _url, download=False):
        raise RuntimeError('ERROR: [PornHub] demo: Unable to download webpage: HTTP Error 410: Gone')


def _thumbnail_expiry(url):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    if 'validto' in query:
        return int(query['validto'][0])
    hdnea = query.get('hdnea', [''])[0]
    match = re.search(r'(?:^|~)exp=(\d+)', hdnea)
    return int(match.group(1)) if match else 0


def test_pornhub_extractor_builds_ytdlp_opts_with_browser_impersonation():
    pornhub_extractor = _load_extractor_module()

    extractor = pornhub_extractor.PornhubExtractor()

    opts = extractor._build_ytdlp_opts('https://www.pornhub.com/view_video.php?viewkey=demo')

    assert str(opts['impersonate']) == 'chrome'


def test_pornhub_extractor_maps_http_410_to_network_error(monkeypatch):
    pornhub_extractor = _load_extractor_module()

    monkeypatch.setattr(pornhub_extractor, 'YoutubeDL', _Http410YoutubeDL)
    extractor = pornhub_extractor.PornhubExtractor()
    monkeypatch.setattr(extractor, '_build_ytdlp_opts', lambda url, queue_name=None: {})

    with pytest.raises(pornhub_extractor.NetworkError) as exc_info:
        extractor._extract_with_ytdlp('https://www.pornhub.com/view_video.php?viewkey=demo')

    assert 'HTTP Error 410' in exc_info.value.context['original_error']


def test_pornhub_extractor_marks_shorties_redirect_as_blocked(monkeypatch):
    pornhub_extractor = _load_extractor_module()

    monkeypatch.setattr(pornhub_extractor, 'YoutubeDL', _FakeYoutubeDL)
    monkeypatch.setattr(
        pornhub_extractor.PornhubExtractor,
        '_resolve_redirect_target',
        lambda self, url, cookie_file=None: 'https://www.pornhub.com/shorties/698e147975244',
        raising=False,
    )

    extractor = pornhub_extractor.PornhubExtractor()
    monkeypatch.setattr(extractor, '_build_ytdlp_opts', lambda url, queue_name=None: {})

    with pytest.raises(pornhub_extractor.ParseError) as exc_info:
        extractor._extract_with_ytdlp('https://www.pornhub.com/view_video.php?viewkey=698e147975244')

    assert exc_info.value.context['blocked_reason_code'] == 'unsupported_short_redirect'
    assert exc_info.value.context['redirect_target'] == 'https://www.pornhub.com/shorties/698e147975244'


def test_pornhub_extractor_rewrites_expiring_preview_thumbnail_from_page_metadata(monkeypatch):
    pornhub_extractor = _load_extractor_module()

    class _PreviewYoutubeDL:
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
                'webpage_url': 'https://www.pornhub.com/view_video.php?viewkey=demo',
                'thumbnail': (
                    'https://pix-cdn77.phncdn.com/c6371/videos/demo/original_demo.mp4/'
                    'plain/ex:1:no/bg:0:0:0/rs:fit:640:360/vts:529?hash=stale&validto=123'
                ),
                'thumbnails': [
                    {
                        'url': (
                            'https://pix-cdn77.phncdn.com/c6371/videos/demo/original_demo.mp4/'
                            'plain/ex:1:no/bg:0:0:0/rs:fit:640:360/vts:529?hash=stale&validto=123'
                        ),
                        'id': '0',
                    }
                ],
            }

    class _FakeResponse:
        status_code = 200
        text = (
            '<meta property="og:image" '
            'content="https://cdn.example.com/thumb.jpg?hash=fresh&amp;validto=456">'
        )

    monkeypatch.setattr(pornhub_extractor, 'YoutubeDL', _PreviewYoutubeDL)
    monkeypatch.setattr(
        pornhub_extractor.requests,
        'get',
        lambda *args, **kwargs: _FakeResponse(),
    )

    extractor = pornhub_extractor.PornhubExtractor()
    monkeypatch.setattr(extractor, '_build_ytdlp_opts', lambda url, queue_name=None: {})

    info = extractor._extract_with_ytdlp('https://www.pornhub.com/view_video.php?viewkey=demo')

    assert info['thumbnail'] == 'https://cdn.example.com/thumb.jpg?hash=fresh&validto=456'
    assert info['thumbnails'][0]['url'] == 'https://cdn.example.com/thumb.jpg?hash=fresh&validto=456'


def test_pornhub_extractor_prefers_long_lived_page_thumbnail(monkeypatch):
    pornhub_extractor = _load_extractor_module()
    short_url = (
        'https://pix-fl.phncdn.com/c6251/videos/demo/original.jpg/plain/'
        'rs:fit:640:360?hdnea=st=1777096861~exp=1777183261~hdl=-1~hmac=short'
    )
    long_url = (
        'https://pix-egi.phncdn.com/c6251/videos/demo/original.jpg/plain/'
        'rs:fit:350:196?validfrom=1751342400&validto=4891363200&hash=long'
    )

    class _FakeResponse:
        status_code = 200
        text = (
            f'<meta property="og:image" content="{short_url}">'
            f'<meta name="twitter:image" content="{long_url}">'
        )

    monkeypatch.setattr(
        pornhub_extractor.requests,
        'get',
        lambda *args, **kwargs: _FakeResponse(),
    )

    extractor = pornhub_extractor.PornhubExtractor()

    assert extractor._fetch_page_thumbnail_url('https://www.pornhub.com/view_video.php?viewkey=demo') == long_url


def test_pornhub_extractor_retries_page_thumbnail_fetch(monkeypatch):
    pornhub_extractor = _load_extractor_module()
    responses = [
        type('Resp', (), {'status_code': 403, 'text': 'blocked'})(),
        type(
            'Resp',
            (),
            {
                'status_code': 200,
                'text': '<meta property="og:image" content="https://cdn.example.com/thumb.jpg?hash=fresh&amp;validto=456">',
            },
        )(),
    ]
    sleep_calls = []

    monkeypatch.setattr(
        pornhub_extractor.requests,
        'get',
        lambda *args, **kwargs: responses.pop(0),
    )
    monkeypatch.setattr(
        pornhub_extractor.time,
        'sleep',
        lambda seconds: sleep_calls.append(seconds),
    )

    extractor = pornhub_extractor.PornhubExtractor()
    thumbnail_url = extractor._fetch_page_thumbnail_url('https://www.pornhub.com/view_video.php?viewkey=demo')

    assert thumbnail_url == 'https://cdn.example.com/thumb.jpg?hash=fresh&validto=456'
    assert sleep_calls == [0.8]
