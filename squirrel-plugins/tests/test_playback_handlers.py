from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
import types
import unittest
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from xml.etree import ElementTree as ET
from unittest.mock import patch


REPO_ROOT = Path(__file__).resolve().parents[2]
JAVDB_HANDLER_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'javdb' / 'src' / 'squirrel_javdb' / 'handler.py'
)
YOUTUBE_MPD_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'youtube' / 'src' / 'squirrel_youtube' / 'mpd.py'
)
YOUTUBE_EXTRACTOR_PATH = (
    REPO_ROOT / 'squirrel-plugins' / 'youtube' / 'src' / 'squirrel_youtube' / 'extractor.py'
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
def _stub_youtube_mpd_dependencies(
    *,
    extract_exception: Exception | None = None,
    extract_callback=None,
    install_youtube_extractor: bool = False,
):
    originals = {
        name: sys.modules.get(name)
        for name in (
            'crawl',
            'requests',
            'yt_dlp',
            'yt_dlp.extractor',
            'yt_dlp.extractor.youtube',
            'yt_dlp.extractor.youtube._video',
        )
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

    class NotFoundError(Exception):
        def __init__(self, message: str, context: dict | None = None):
            super().__init__(message)
            self.message = message
            self.context = context or {}

    class YoutubeDLExtractorBase:
        def __init__(self, site_name: str, supported_domains: list[str]):
            self.site_name = site_name
            self.supported_domains = supported_domains

    crawl_module.AuthError = AuthError
    crawl_module.NetworkError = NetworkError
    crawl_module.ParseError = ParseError
    crawl_module.NotFoundError = NotFoundError
    crawl_module.YoutubeDLExtractorBase = YoutubeDLExtractorBase
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
    yt_dlp_module.__path__ = []  # type: ignore[attr-defined]

    class FakeYoutubeDL:
        last_opts = None
        last_process = None

        def __init__(self, opts):
            type(self).last_opts = dict(opts)

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url: str, download: bool = False, process: bool = True):
            type(self).last_process = process
            if extract_exception is not None:
                raise extract_exception
            if extract_callback is not None:
                return extract_callback(_url, download, process)
            return {'formats': []}

    yt_dlp_module.YoutubeDL = FakeYoutubeDL

    yt_dlp_extractor_module = types.ModuleType('yt_dlp.extractor')
    yt_dlp_extractor_module.__path__ = []  # type: ignore[attr-defined]
    yt_dlp_youtube_module = types.ModuleType('yt_dlp.extractor.youtube')
    yt_dlp_youtube_module.__path__ = []  # type: ignore[attr-defined]
    yt_dlp_youtube_video_module = types.ModuleType('yt_dlp.extractor.youtube._video')

    if install_youtube_extractor:
        class YoutubeIE:
            def _extract_player_responses(self, *_args, **_kwargs):
                return ([
                    {
                        'streamingData': {
                            'adaptiveFormats': [{
                                'itag': 313,
                                'url': 'https://cdn.example.com/313.webm',
                                'initRange': {'start': '0', 'end': '1'},
                                'indexRange': {'start': '2', 'end': '3'},
                            }],
                            '__yt_dlp_fetch_gvs_po_token': lambda: 'token',
                        },
                        'responseContext': {'visitorData': 'visitor-data'},
                    }
                ], 'https://youtube.com/s/player/demo.js')

            def _real_extract(self, url):
                self._extract_player_responses(None, None, None, None, None, None)
                return {'id': 'demo', 'webpage_url': url, 'formats': []}

        yt_dlp_youtube_video_module.YoutubeIE = YoutubeIE

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['requests'] = requests_module
        sys.modules['yt_dlp'] = yt_dlp_module
        sys.modules['yt_dlp.extractor'] = yt_dlp_extractor_module
        sys.modules['yt_dlp.extractor.youtube'] = yt_dlp_youtube_module
        sys.modules['yt_dlp.extractor.youtube._video'] = yt_dlp_youtube_video_module
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


def _load_youtube_extractor_module():
    module_name = '_extractor_test_youtube'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YOUTUBE_EXTRACTOR_PATH)
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

    def test_youtube_mpd_opts_use_default_player_client_without_cookies(self):
        with _stub_youtube_mpd_dependencies() as (FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            opts = module._build_ytdlp_opts('https://youtube.com/watch?v=demo')

            self.assertEqual(opts['extractor_args']['youtube']['player_client'], [module.YOUTUBE_PLAYER_CLIENT])
            self.assertEqual(opts['socket_timeout'], 30)
            self.assertEqual(opts['retries'], 5)
            self.assertEqual(FakeYoutubeDL.last_opts, None)

    def test_youtube_mpd_opts_use_cookie_compatible_clients_when_pot_provider_disabled(self):
        with _stub_youtube_mpd_dependencies() as (FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()
            module.youtube_ytdlp_support.resolve_cookie_file_path = lambda _url: 'C:/tmp/youtube.txt'

            with patch.dict('os.environ', {'SQUIRREL_YOUTUBE_POT_PROVIDER_MODE': 'off'}, clear=False):
                opts = module._build_ytdlp_opts('https://youtube.com/watch?v=demo')

            self.assertEqual(opts['extractor_args']['youtube']['player_client'], module.YOUTUBE_COOKIE_PLAYER_CLIENTS)
            self.assertEqual(opts['cookiefile'], 'C:/tmp/youtube.txt')
            self.assertNotIn('youtubepot-bgutilscript', opts['extractor_args'])
            self.assertEqual(FakeYoutubeDL.last_opts, None)

    def test_youtube_mpd_opts_use_mweb_when_script_provider_is_available(self):
        with _stub_youtube_mpd_dependencies() as (FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()
            module.youtube_ytdlp_support.resolve_cookie_file_path = lambda _url: 'C:/tmp/youtube.txt'

            with tempfile.TemporaryDirectory() as tmpdir:
                server_home = Path(tmpdir)
                build_dir = server_home / 'build'
                build_dir.mkdir(parents=True, exist_ok=True)
                (build_dir / 'generate_once.js').write_text('// test helper\n', encoding='utf-8')

                with patch.dict('os.environ', {
                    'SQUIRREL_YOUTUBE_POT_PROVIDER_MODE': 'script',
                    'SQUIRREL_YOUTUBE_POT_PROVIDER_SERVER_HOME': str(server_home),
                }, clear=False):
                    module.youtube_ytdlp_support._has_bgutil_script_plugin = lambda: True
                    module.youtube_ytdlp_support._has_bgutil_http_plugin = lambda: False
                    module.youtube_ytdlp_support.shutil.which = lambda name: 'C:/node.exe' if name == 'node' else None

                    opts = module._build_ytdlp_opts('https://youtube.com/watch?v=demo')

            self.assertEqual(opts['extractor_args']['youtube']['player_client'], ['mweb'])
            self.assertEqual(
                opts['extractor_args']['youtubepot-bgutilscript']['server_home'],
                [str(server_home)]
            )
            self.assertEqual(opts['cookiefile'], 'C:/tmp/youtube.txt')
            self.assertEqual(FakeYoutubeDL.last_opts, None)

    def test_youtube_extract_info_with_player_responses_preserves_streaming_data(self):
        def _extract_callback(url: str, _download: bool = False, _process: bool = True):
            YoutubeIE = sys.modules['yt_dlp.extractor.youtube._video'].YoutubeIE
            return YoutubeIE()._real_extract(url)

        with _stub_youtube_mpd_dependencies(
            extract_callback=_extract_callback,
            install_youtube_extractor=True,
        ) as (_FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            info = module.youtube_ytdlp_support.extract_info_with_player_responses(
                'https://youtube.com/watch?v=demo',
                {'quiet': True},
            )

            self.assertEqual(info[module.youtube_ytdlp_support.YOUTUBE_PLAYER_URL_INFO_KEY], 'https://youtube.com/s/player/demo.js')
            player_responses = info[module.youtube_ytdlp_support.YOUTUBE_PLAYER_RESPONSES_INFO_KEY]
            self.assertEqual(player_responses[0]['streamingData']['adaptiveFormats'][0]['itag'], 313)
            self.assertEqual(
                player_responses[0]['streamingData']['adaptiveFormats'][0]['initRange'],
                {'start': '0', 'end': '1'},
            )
            self.assertNotIn('__yt_dlp_fetch_gvs_po_token', player_responses[0]['streamingData'])

    def test_youtube_extract_info_retries_without_bgutil_script_provider_on_timeout(self):
        calls = []

        def _extract_callback(_url: str, _download: bool = False, _process: bool = True):
            extractor_args = dict((FakeYoutubeDL.last_opts or {}).get('extractor_args') or {})
            calls.append(extractor_args)
            if 'youtubepot-bgutilscript' in extractor_args:
                raise subprocess.TimeoutExpired(
                    cmd=['C:/node.exe', 'C:/bgutil/server/build/generate_once.js', '--version'],
                    timeout=15.0,
                )
            return {'id': 'demo'}

        with _stub_youtube_mpd_dependencies(
            extract_callback=_extract_callback,
        ) as (FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            info = module.youtube_ytdlp_support.extract_info_with_player_responses(
                'https://youtube.com/watch?v=demo',
                {
                    'quiet': True,
                    'extractor_args': {
                        'youtube': {
                            'player_client': ['mweb'],
                        },
                        'youtubepot-bgutilscript': {
                            'server_home': ['C:/bgutil/server'],
                        },
                    },
                },
            )

            self.assertEqual(info, {'id': 'demo'})
            self.assertEqual(len(calls), 2)
            self.assertIn('youtubepot-bgutilscript', calls[0])
            self.assertNotIn('youtubepot-bgutilscript', calls[1])
            self.assertEqual(
                calls[1]['youtube']['player_client'],
                module.youtube_ytdlp_support.YOUTUBE_COOKIE_PLAYER_CLIENTS,
            )

    def test_youtube_extractor_uses_unprocessed_info_for_metadata_extraction(self):
        def _extract_callback(_url: str, _download: bool = False, process: bool = True):
            if process:
                raise RuntimeError(
                    'ERROR: [youtube] demo: Requested format is not available. '
                    'Use --list-formats for a list of available formats'
                )
            return {
                'id': 'demo',
                'title': 'Demo title',
                'timestamp': 1712345678,
                'formats': [],
            }

        with _stub_youtube_mpd_dependencies(
            extract_callback=_extract_callback,
        ) as (FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_extractor_module()

            info = module.YoutubeExtractor()._extract_with_ytdlp('https://youtube.com/watch?v=demo')

            self.assertEqual(info['title'], 'Demo title')
            self.assertFalse(FakeYoutubeDL.last_process)
            self.assertIsNotNone(info.get('publish_date'))

    def test_youtube_extract_video_info_raises_auth_error_for_sign_in_failures(self):
        with _stub_youtube_mpd_dependencies(
            extract_exception=RuntimeError('Sign in to confirm you’re not a bot'),
        ) as (_FakeYoutubeDL, AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            with self.assertRaises(AuthError):
                module._extract_video_info('https://youtube.com/watch?v=demo')

    def test_youtube_format_to_rep_skips_probe_when_disabled(self):
        with _stub_youtube_mpd_dependencies() as (_FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()
            probe_calls = {'count': 0}

            def _probe(*_args, **_kwargs):
                probe_calls['count'] += 1
                return ('0-1', '2-3')

            module._probe_webm_ranges = _probe

            rep = module._format_to_rep({
                'format_id': '244',
                'url': 'https://cdn.example.com/video.webm',
                'ext': 'webm',
                'vcodec': 'vp9',
                'acodec': 'none',
                'height': 720,
                'mime_type': 'video/webm',
            }, allow_probe=False)

            self.assertIsNone(rep)
            self.assertEqual(probe_calls['count'], 0)

    def test_youtube_select_dash_probe_formats_limits_candidates(self):
        with _stub_youtube_mpd_dependencies() as (_FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            selected = module._select_dash_probe_formats([
                {'format_id': '299', 'url': 'https://cdn.example.com/299.mp4', 'ext': 'mp4', 'height': 1080, 'tbr': 1700, 'vcodec': 'avc1.64002a', 'acodec': 'none'},
                {'format_id': '303', 'url': 'https://cdn.example.com/303.webm', 'ext': 'webm', 'height': 1080, 'tbr': 1110, 'vcodec': 'vp9', 'acodec': 'none'},
                {'format_id': '136', 'url': 'https://cdn.example.com/136.mp4', 'ext': 'mp4', 'height': 720, 'tbr': 680, 'vcodec': 'avc1.64001f', 'acodec': 'none'},
                {'format_id': '247', 'url': 'https://cdn.example.com/247.webm', 'ext': 'webm', 'height': 720, 'tbr': 490, 'vcodec': 'vp9', 'acodec': 'none'},
                {'format_id': '135', 'url': 'https://cdn.example.com/135.mp4', 'ext': 'mp4', 'height': 480, 'tbr': 360, 'vcodec': 'avc1.4d401f', 'acodec': 'none'},
                {'format_id': '134', 'url': 'https://cdn.example.com/134.mp4', 'ext': 'mp4', 'height': 360, 'tbr': 210, 'vcodec': 'avc1.4d401e', 'acodec': 'none'},
                {'format_id': '133', 'url': 'https://cdn.example.com/133.mp4', 'ext': 'mp4', 'height': 240, 'tbr': 100, 'vcodec': 'avc1.4d4015', 'acodec': 'none'},
                {'format_id': '251-drc', 'url': 'https://cdn.example.com/251.webm', 'ext': 'webm', 'abr': 141, 'format_note': 'English original default, medium, DRC', 'language': 'en-US', 'vcodec': 'none', 'acodec': 'opus'},
                {'format_id': '140-7', 'url': 'https://cdn.example.com/140.m4a', 'ext': 'm4a', 'abr': 129, 'format_note': 'English original default, medium', 'language': 'en-US', 'vcodec': 'none', 'acodec': 'mp4a.40.2'},
            ])

            self.assertEqual([fmt['format_id'] for fmt in selected], ['299', '136', '135', '134', '140-7'])

    def test_youtube_select_dash_probe_formats_keeps_high_res_codec_fallback(self):
        with _stub_youtube_mpd_dependencies() as (_FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            selected = module._select_dash_probe_formats([
                {'format_id': '401', 'url': 'https://cdn.example.com/401.mp4', 'ext': 'mp4', 'height': 2160, 'tbr': 11962, 'vcodec': 'av01.0.12M.08', 'acodec': 'none'},
                {'format_id': '313', 'url': 'https://cdn.example.com/313.webm', 'ext': 'webm', 'height': 2160, 'tbr': 10828, 'vcodec': 'vp9', 'acodec': 'none'},
                {'format_id': '400', 'url': 'https://cdn.example.com/400.mp4', 'ext': 'mp4', 'height': 1440, 'tbr': 6487, 'vcodec': 'av01.0.12M.08', 'acodec': 'none'},
                {'format_id': '271', 'url': 'https://cdn.example.com/271.webm', 'ext': 'webm', 'height': 1440, 'tbr': 5542, 'vcodec': 'vp9', 'acodec': 'none'},
                {'format_id': '137', 'url': 'https://cdn.example.com/137.mp4', 'ext': 'mp4', 'height': 1080, 'tbr': 4270, 'vcodec': 'avc1.640028', 'acodec': 'none'},
                {'format_id': '399', 'url': 'https://cdn.example.com/399.mp4', 'ext': 'mp4', 'height': 1080, 'tbr': 2545, 'vcodec': 'av01.0.08M.08', 'acodec': 'none'},
                {'format_id': '136', 'url': 'https://cdn.example.com/136.mp4', 'ext': 'mp4', 'height': 720, 'tbr': 2063, 'vcodec': 'avc1.64001f', 'acodec': 'none'},
                {'format_id': '140-7', 'url': 'https://cdn.example.com/140.m4a', 'ext': 'm4a', 'abr': 129, 'format_note': 'English original default, medium', 'language': 'en-US', 'vcodec': 'none', 'acodec': 'mp4a.40.2'},
            ])

            self.assertEqual(
                [fmt['format_id'] for fmt in selected],
                ['401', '313', '400', '271', '137', '136', '140-7']
            )

    def test_youtube_build_dash_representations_prefers_streaming_data(self):
        with _stub_youtube_mpd_dependencies() as (_FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()
            module._probe_mp4_ranges = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('mp4 probe should not run'))
            module._probe_webm_ranges = lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError('webm probe should not run'))

            info = {
                'formats': [
                    {'format_id': '401', 'url': 'https://cdn.example.com/401.mp4?pot=video-pot', 'ext': 'mp4', 'height': 2160, 'tbr': 11962, 'vcodec': 'av01.0.12M.08', 'acodec': 'none'},
                    {'format_id': '313', 'url': 'https://cdn.example.com/313.webm?pot=video-pot', 'ext': 'webm', 'height': 2160, 'tbr': 10828, 'vcodec': 'vp9', 'acodec': 'none'},
                    {'format_id': '137', 'url': 'https://cdn.example.com/137.mp4?pot=video-pot', 'ext': 'mp4', 'height': 1080, 'tbr': 4270, 'vcodec': 'avc1.640028', 'acodec': 'none'},
                    {'format_id': '136', 'url': 'https://cdn.example.com/136.mp4?pot=video-pot', 'ext': 'mp4', 'height': 720, 'tbr': 2063, 'vcodec': 'avc1.64001f', 'acodec': 'none'},
                    {'format_id': '140', 'url': 'https://cdn.example.com/140.m4a?pot=audio-pot', 'ext': 'm4a', 'abr': 129, 'vcodec': 'none', 'acodec': 'mp4a.40.2', 'language': 'en-US', 'format_note': 'English original default'},
                ],
                module.youtube_ytdlp_support.YOUTUBE_PLAYER_RESPONSES_INFO_KEY: [
                    {
                        'streamingData': {
                            'adaptiveFormats': [
                                {'itag': 313, 'url': 'https://cdn.example.com/313.webm', 'mimeType': 'video/webm; codecs="vp9"', 'qualityLabel': '2160p', 'width': 2160, 'height': 3840, 'bitrate': 10828000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 401, 'url': 'https://cdn.example.com/401.mp4', 'mimeType': 'video/mp4; codecs="av01.0.12M.08"', 'qualityLabel': '2160p', 'width': 2160, 'height': 3840, 'bitrate': 11962000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 271, 'url': 'https://cdn.example.com/271.webm', 'mimeType': 'video/webm; codecs="vp9"', 'qualityLabel': '1440p', 'width': 1440, 'height': 2560, 'bitrate': 5542000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 400, 'url': 'https://cdn.example.com/400.mp4', 'mimeType': 'video/mp4; codecs="av01.0.12M.08"', 'qualityLabel': '1440p', 'width': 1440, 'height': 2560, 'bitrate': 6487000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 137, 'url': 'https://cdn.example.com/137.mp4', 'mimeType': 'video/mp4; codecs="avc1.640028"', 'qualityLabel': '1080p', 'width': 1080, 'height': 1920, 'bitrate': 4270000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 248, 'url': 'https://cdn.example.com/248.webm', 'mimeType': 'video/webm; codecs="vp9"', 'qualityLabel': '1080p', 'width': 1080, 'height': 1920, 'bitrate': 3012000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 399, 'url': 'https://cdn.example.com/399.mp4', 'mimeType': 'video/mp4; codecs="av01.0.08M.08"', 'qualityLabel': '1080p', 'width': 1080, 'height': 1920, 'bitrate': 2545000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 136, 'url': 'https://cdn.example.com/136.mp4', 'mimeType': 'video/mp4; codecs="avc1.64001f"', 'qualityLabel': '720p', 'width': 720, 'height': 1280, 'bitrate': 2063000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 140, 'url': 'https://cdn.example.com/140.m4a', 'mimeType': 'audio/mp4; codecs="mp4a.40.2"', 'bitrate': 129000, 'audioSampleRate': '44100', 'audioChannels': 2, 'audioTrack': {'id': 'en-US.1', 'displayName': 'English original', 'audioIsDefault': True}, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                            ],
                        },
                    },
                ],
            }

            reps = module._build_dash_representations(info)

            self.assertEqual(
                {rep['id'] for rep in reps if rep['kind'] == 'video'},
                {'401', '313', '400', '271', '137', '248', '399', '136'},
            )
            self.assertEqual({rep['id'] for rep in reps if rep['kind'] == 'audio'}, {'140'})
            self.assertTrue(all(rep.get('initRange') and rep.get('indexRange') for rep in reps))
            self.assertEqual(next(rep['url'] for rep in reps if rep['id'] == '401'), 'https://cdn.example.com/401.mp4?pot=video-pot')
            self.assertEqual(next(rep['url'] for rep in reps if rep['id'] == '140'), 'https://cdn.example.com/140.m4a?pot=audio-pot')

    def test_youtube_mpd_builder_includes_upstream_referer_in_proxy_urls(self):
        with _stub_youtube_mpd_dependencies() as (_FakeYoutubeDL, _AuthError, _NetworkError, _ParseError):
            module = _load_youtube_mpd_module()

            info = {
                'webpage_url': 'https://m.youtube.com/watch?v=demo',
                module.youtube_ytdlp_support.YOUTUBE_PLAYER_RESPONSES_INFO_KEY: [
                    {
                        'streamingData': {
                            'adaptiveFormats': [
                                {'itag': 401, 'url': 'https://cdn.example.com/401.mp4', 'mimeType': 'video/mp4; codecs="av01.0.12M.08"', 'qualityLabel': '2160p', 'width': 2160, 'height': 3840, 'bitrate': 11962000, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                                {'itag': 140, 'url': 'https://cdn.example.com/140.m4a', 'mimeType': 'audio/mp4; codecs="mp4a.40.2"', 'bitrate': 129000, 'audioSampleRate': '44100', 'audioChannels': 2, 'audioTrack': {'id': 'en-US.1', 'displayName': 'English original', 'audioIsDefault': True}, 'initRange': {'start': '0', 'end': '1'}, 'indexRange': {'start': '2', 'end': '3'}},
                            ],
                        },
                    },
                ],
            }

            module._extract_video_info = lambda _url: info
            xml_text = module.YouTubeMpdBuilder().build_mpd(types.SimpleNamespace(url='https://youtube.com/watch?v=demo'))
            root = ET.fromstring(xml_text)
            base_urls = [node.text for node in root.findall('.//{urn:mpeg:dash:schema:mpd:2011}BaseURL')]

            self.assertTrue(base_urls)
            parsed = urlparse(base_urls[0])
            query = parse_qs(parsed.query)
            self.assertEqual(query['referer'], ['https://m.youtube.com/watch?v=demo'])


if __name__ == '__main__':
    unittest.main()
