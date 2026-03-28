from __future__ import annotations

import importlib.util
import sys
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
JAVDB_HANDLER_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'javdb' / 'src' / 'squirrel_javdb' / 'handler.py'
)
YOUTUBE_MPD_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'youtube' / 'src' / 'squirrel_youtube' / 'mpd.py'
)


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeAnchor:
    def __init__(self, href: str | None) -> None:
        self._href = href

    def get(self, key: str, default=None):
        if key == 'href':
            return self._href
        return default


class _FakeThumbnail:
    def __init__(self, href: str | None) -> None:
        self._anchor = _FakeAnchor(href)

    def select_one(self, selector: str):
        if selector == 'a':
            return self._anchor
        return None


class _FakeScriptTag:
    def __init__(self, string: str | None = None, text: str | None = None) -> None:
        self.string = string
        self._text = text if text is not None else string

    def get_text(self) -> str:
        return self._text or ''


class _FakeSoup:
    def __init__(
        self,
        *,
        select_map: dict[str, list[object]] | None = None,
        find_all_map: dict[str, list[object]] | None = None,
    ) -> None:
        self.select_map = select_map or {}
        self.find_all_map = find_all_map or {}

    def select(self, selector: str):
        return list(self.select_map.get(selector, []))

    def find_all(self, name: str):
        return list(self.find_all_map.get(name, []))


@contextmanager
def _stub_javdb_handler_dependencies():
    originals = {name: sys.modules.get(name) for name in ('crawl', 'bs4')}
    responses: list[_FakeResponse] = []
    soup_registry: dict[str, _FakeSoup] = {}

    crawl_module = types.ModuleType('crawl')

    class ParseError(Exception):
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    class NetworkError(Exception):
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    def request_without_limit(_method: str, _url: str, **_kwargs):
        if not responses:
            raise AssertionError('No queued response for request_without_limit')
        return responses.pop(0)

    crawl_module.request_without_limit = request_without_limit
    crawl_module.ParseError = ParseError
    crawl_module.NetworkError = NetworkError

    bs4_module = types.ModuleType('bs4')
    bs4_module.BeautifulSoup = lambda html, _parser: soup_registry[html]

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['bs4'] = bs4_module
        yield responses, soup_registry, ParseError, NetworkError
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_javdb_handler_module():
    module_name = '_handler_test_javdb'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, JAVDB_HANDLER_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


@contextmanager
def _stub_youtube_mpd_dependencies(*, extract_exception: Exception | None = None):
    originals = {
        name: sys.modules.get(name)
        for name in ('crawl', 'requests', 'yt_dlp')
    }

    crawl_module = types.ModuleType('crawl')

    class AuthError(Exception):
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    class NetworkError(Exception):
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    class ParseError(Exception):
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    crawl_module.AuthError = AuthError
    crawl_module.NetworkError = NetworkError
    crawl_module.ParseError = ParseError
    crawl_module.apply_ytdlp_rate_limit = lambda _site, opts: dict(opts)
    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.resolve_cookie_file_path = lambda _url: None
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})

    requests_module = types.ModuleType('requests')

    class Session:
        def get(self, *args, **kwargs):
            raise AssertionError('Network probing should not run in this test')

    requests_module.Session = Session

    yt_dlp_module = types.ModuleType('yt_dlp')

    class FakeYoutubeDL:
        last_opts = None

        def __init__(self, opts):
            type(self).last_opts = dict(opts)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url: str, download: bool = False):
            if extract_exception is not None:
                raise extract_exception
            return {'formats': []}

    yt_dlp_module.YoutubeDL = FakeYoutubeDL

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['requests'] = requests_module
        sys.modules['yt_dlp'] = yt_dlp_module
        yield FakeYoutubeDL, AuthError, NetworkError, ParseError
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_youtube_mpd_module():
    module_name = '_mpd_test_youtube'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YOUTUBE_MPD_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


class PlaybackHandlerTests(unittest.TestCase):
    def test_javdb_handler_resolves_relative_detail_links(self):
        with _stub_javdb_handler_dependencies() as (responses, soups, _parse_error, _network_error):
            module = _load_javdb_handler_module()

            responses.extend([
                _FakeResponse('search-page'),
                _FakeResponse('detail-page'),
            ])
            soups['search-page'] = _FakeSoup(select_map={
                'div.thumbnail': [_FakeThumbnail('/en/ABP-123')],
            })
            soups['detail-page'] = _FakeSoup(find_all_map={
                'script': [
                    _FakeScriptTag(text="'m3u8|one|two|three|four|five|com|example|cdn|videos|https|video|master|playlist|source'"),
                ],
            })

            payload = module.JavdbHandler().get_video_url(types.SimpleNamespace(title='ABP-123 Demo Title'))

            self.assertIsNone(payload['audio_url'])
            parsed = urlparse(payload['video_url'])
            query = parse_qs(parsed.query)
            self.assertEqual(unquote(query['referer'][0]), 'https://missav.ai/en/ABP-123')
            self.assertEqual(unquote(query['url'][0]), 'https://videos.cdn.example.com/five-four-three-two-one/master/video.m3u8')

    def test_javdb_handler_raises_parse_error_when_stream_cannot_be_resolved(self):
        with _stub_javdb_handler_dependencies() as (responses, soups, ParseError, _network_error):
            module = _load_javdb_handler_module()

            responses.append(_FakeResponse('search-page'))
            soups['search-page'] = _FakeSoup(select_map={'div.thumbnail': []})

            with self.assertRaises(ParseError):
                module.JavdbHandler().get_video_url(types.SimpleNamespace(title='ABP-123 Demo Title'))

    def test_youtube_mpd_opts_use_android_player_client_for_playback(self):
        with _stub_youtube_mpd_dependencies() as (FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            opts = module._build_ytdlp_opts('https://youtube.com/watch?v=demo')

            self.assertEqual(opts['extractor_args']['youtube']['player_client'], [module.YOUTUBE_PLAYER_CLIENT])
            self.assertEqual(opts['socket_timeout'], 30)
            self.assertEqual(opts['retries'], 5)
            self.assertEqual(FakeYoutubeDL.last_opts, None)

    def test_youtube_extract_video_info_raises_auth_error_for_sign_in_failures(self):
        with _stub_youtube_mpd_dependencies(
            extract_exception=RuntimeError('Sign in to confirm you’re not a bot'),
        ) as (_FakeYoutubeDL, AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            with self.assertRaises(AuthError):
                module._extract_video_info('https://youtube.com/watch?v=demo')


if __name__ == '__main__':
    unittest.main()
