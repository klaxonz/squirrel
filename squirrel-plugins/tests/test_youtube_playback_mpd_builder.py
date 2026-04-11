from __future__ import annotations

import importlib
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
YOUTUBE_SRC = ROOT / 'squirrel-plugins' / 'youtube' / 'src'


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
def _stub_mpd_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'crawl',
            'requests',
            'squirrel_youtube',
            'squirrel_youtube.ytdlp_support',
        )
    }

    crawl_module = types.ModuleType('crawl')
    crawl_module.AuthError = RuntimeError
    crawl_module.NetworkError = RuntimeError
    crawl_module.ParseError = RuntimeError
    crawl_module.apply_ytdlp_rate_limit = lambda _site, opts: opts
    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.get_http_headers = lambda _site, headers=None: dict(headers or {})

    requests_module = types.ModuleType('requests')

    class Session:
        def get(self, *_args, **_kwargs):
            raise AssertionError('network probing should not run in this test')

    requests_module.Session = Session

    support_module = types.ModuleType('squirrel_youtube.ytdlp_support')
    support_module.YOUTUBE_PLAYER_CLIENT = 'android'
    support_module.YOUTUBE_COOKIE_PLAYER_CLIENTS = ['tv', 'web']
    support_module.YOUTUBE_PLAYER_RESPONSES_INFO_KEY = '__player_responses__'

    package_module = types.ModuleType('squirrel_youtube')
    package_module.__path__ = [str(YOUTUBE_SRC / 'squirrel_youtube')]  # type: ignore[attr-defined]

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['requests'] = requests_module
        sys.modules['squirrel_youtube'] = package_module
        sys.modules['squirrel_youtube.ytdlp_support'] = support_module
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_youtube_mpd_builder_prefers_youtubei_formats(monkeypatch):
    with _stub_mpd_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.mpd')
        resolver_module = importlib.import_module('squirrel_youtube.youtubei_resolver')

        monkeypatch.setattr(
            module,
            'resolve_with_youtubei',
            lambda _video_id, timeout_seconds=10.0, resolution_mode='playback': resolver_module.YoutubeiResult(
                client='ANDROID',
                playability_status='OK',
                formats=[
                    resolver_module.YoutubeiFormat(
                        itag=137,
                        mime_type='video/mp4; codecs="avc1.640028"',
                        quality_label='1080p',
                        url='https://cdn.example.test/137',
                        has_audio=False,
                        has_video=True,
                        bitrate=4000000,
                        width=1920,
                        height=1080,
                        audio_quality=None,
                        audio_sample_rate=None,
                        audio_channels=None,
                        init_range='0-741',
                        index_range='742-1229',
                        content_length=80911999,
                        language=None,
                    ),
                    resolver_module.YoutubeiFormat(
                        itag=140,
                        mime_type='audio/mp4; codecs="mp4a.40.2"',
                        quality_label='tiny',
                        url='https://cdn.example.test/140',
                        has_audio=True,
                        has_video=False,
                        bitrate=128000,
                        width=None,
                        height=None,
                        audio_quality='AUDIO_QUALITY_MEDIUM',
                        audio_sample_rate='44100',
                        audio_channels=2,
                        init_range='0-703',
                        index_range='704-1003',
                        content_length=3400000,
                        language='en',
                    ),
                ],
            ),
        )
        monkeypatch.setattr(module, '_extract_video_info', lambda _url: (_ for _ in ()).throw(AssertionError('yt-dlp fallback should not run')))

        builder = module.YouTubeMpdBuilder()
        xml = builder.build_mpd(SimpleNamespace(id=123, url='https://www.youtube.com/watch?v=demo', duration=213))

        assert 'Representation id="137"' in xml
        assert 'Representation id="140"' in xml
        assert '/api/video/proxy?domain=youtube.com' in xml
        assert 'indexRange="742-1229"' in xml


def test_youtube_mpd_builder_uses_watch_id_instead_of_database_id(monkeypatch):
    with _stub_mpd_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.mpd')
        resolver_module = importlib.import_module('squirrel_youtube.youtubei_resolver')
        captured = {}

        monkeypatch.setattr(
            module,
            'resolve_with_youtubei',
            lambda video_id, timeout_seconds=10.0, resolution_mode='playback': (
                captured.setdefault('video_id', video_id),
                captured.setdefault('resolution_mode', resolution_mode),
                resolver_module.YoutubeiResult(
                    client='ANDROID',
                    playability_status='OK',
                    formats=[],
                ),
            )[-1],
        )
        monkeypatch.setattr(module, '_extract_video_info', lambda _url: (_ for _ in ()).throw(RuntimeError('fallback')))

        try:
            module.YouTubeMpdBuilder().build_mpd(
                SimpleNamespace(id=123, url='https://www.youtube.com/watch?v=z0NnBVMqo64', duration=213)
            )
        except Exception:
            pass

        assert captured['video_id'] == 'z0NnBVMqo64'
        assert captured['resolution_mode'] == 'all'


def test_youtubei_representation_derives_init_range_from_index_range():
    with _stub_mpd_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.mpd')
        resolver_module = importlib.import_module('squirrel_youtube.youtubei_resolver')

        rep = module._youtubei_representation(
            resolver_module.YoutubeiFormat(
                itag=401,
                mime_type='video/mp4; codecs="av01.0.12M.08"',
                quality_label='2160p',
                url='https://cdn.example.test/401',
                has_audio=False,
                has_video=True,
                bitrate=1000,
                width=3840,
                height=2160,
                audio_quality=None,
                audio_sample_rate=None,
                audio_channels=None,
                init_range=None,
                index_range='701-984',
                content_length=123,
                language=None,
            )
        )

        assert rep is not None
        assert rep['initRange'] == '0-700'


def test_mpd_builder_does_not_emit_empty_initialization_node():
    with _stub_mpd_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.mpd')

        xml = module._build_mpd_from_representations(
            SimpleNamespace(id=123, url='https://www.youtube.com/watch?v=demo', duration=100),
            [
                {
                    'id': '137',
                    'bandwidth': 1000,
                    'mime': 'video/mp4',
                    'codecs': 'avc1.640028',
                    'url': 'https://cdn.example.test/137',
                    'width': 1920,
                    'height': 1080,
                    'fps': None,
                    'audioSamplingRate': None,
                    'audioChannels': None,
                    'initRange': None,
                    'indexRange': '701-984',
                    'kind': 'video',
                    'codecFamily': 'avc',
                    'xml_lang': None,
                    'label': '1080p',
                }
            ],
            'https://www.youtube.com/watch?v=demo',
            100,
        )

        assert '<Initialization />' not in xml
        assert '<Initialization' not in xml


def test_youtube_mpd_builder_returns_direct_base_urls_when_requested(monkeypatch):
    with _stub_mpd_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.mpd')

        xml = module._build_mpd_from_representations(
            SimpleNamespace(
                id=123,
                url='https://www.youtube.com/watch?v=demo',
                duration=100,
                direct_playback=True,
            ),
            [
                {
                    'id': '137',
                    'bandwidth': 1000,
                    'mime': 'video/mp4',
                    'codecs': 'avc1.640028',
                    'url': 'https://cdn.example.test/137',
                    'width': 1920,
                    'height': 1080,
                    'fps': None,
                    'audioSamplingRate': None,
                    'audioChannels': None,
                    'initRange': None,
                    'indexRange': '701-984',
                    'kind': 'video',
                    'codecFamily': 'avc',
                    'xml_lang': None,
                    'label': '1080p',
                }
            ],
            'https://www.youtube.com/watch?v=demo',
            100,
        )

        assert 'https://cdn.example.test/137' in xml
        assert '/api/video/proxy?domain=youtube.com' not in xml
