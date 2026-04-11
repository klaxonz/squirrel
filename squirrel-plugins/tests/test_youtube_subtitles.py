from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace


ROOT = Path(__file__).resolve().parents[2]
YOUTUBE_SRC = ROOT / 'squirrel-plugins' / 'youtube' / 'src'
YOUTUBE_PACKAGE = YOUTUBE_SRC / 'squirrel_youtube'
SUBTITLES_PATH = YOUTUBE_PACKAGE / 'subtitles.py'


@contextmanager
def _stub_crawl_module():
    original = sys.modules.get('crawl')
    crawl_module = types.ModuleType('crawl')
    crawl_module.SubtitlesProvider = object
    crawl_module.resolve_cookie_file_path = lambda _url: None
    try:
        sys.modules['crawl'] = crawl_module
        yield crawl_module
    finally:
        if original is None:
            sys.modules.pop('crawl', None)
        else:
            sys.modules['crawl'] = original


@contextmanager
def _stub_yt_dlp_module(youtube_dl_cls):
    original = sys.modules.get('yt_dlp')
    yt_dlp_module = types.ModuleType('yt_dlp')
    yt_dlp_module.YoutubeDL = youtube_dl_cls
    try:
        sys.modules['yt_dlp'] = yt_dlp_module
        yield yt_dlp_module
    finally:
        if original is None:
            sys.modules.pop('yt_dlp', None)
        else:
            sys.modules['yt_dlp'] = original


@contextmanager
def _stub_youtube_support_module():
    package_original = sys.modules.get('squirrel_youtube')
    support_original = sys.modules.get('squirrel_youtube.ytdlp_support')

    package_module = types.ModuleType('squirrel_youtube')
    package_module.__path__ = [str(YOUTUBE_PACKAGE)]
    support_module = types.ModuleType('squirrel_youtube.ytdlp_support')
    support_module.YOUTUBE_PLAYER_CLIENT = 'android'
    support_module.apply_youtube_player_strategy = lambda _url, _opts: None

    try:
        sys.modules['squirrel_youtube'] = package_module
        sys.modules['squirrel_youtube.ytdlp_support'] = support_module
        yield support_module
    finally:
        if package_original is None:
            sys.modules.pop('squirrel_youtube', None)
        else:
            sys.modules['squirrel_youtube'] = package_original
        if support_original is None:
            sys.modules.pop('squirrel_youtube.ytdlp_support', None)
        else:
            sys.modules['squirrel_youtube.ytdlp_support'] = support_original


def _load_subtitles_module():
    module_name = 'squirrel_youtube.subtitles'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, SUBTITLES_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


def test_youtube_subtitles_retry_without_cookie_strategy(monkeypatch):
    calls = []

    class _FakeYoutubeDL:
        def __init__(self, opts):
            self.opts = dict(opts)

        def __enter__(self):
            calls.append(self.opts)
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, _urls):
            if self.opts.get('cookiefile'):
                raise Exception('ERROR: [youtube] demo: Requested format is not available.')
            outdir = Path(self.opts['outtmpl']).parent
            (outdir / 'demo.en.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nhello\n', encoding='utf-8')

    with _stub_crawl_module() as crawl_module, _stub_yt_dlp_module(_FakeYoutubeDL), _stub_youtube_support_module() as support_module:
        crawl_module.resolve_cookie_file_path = lambda _url: 'D:/Code/init/squirrel/config/site_cookies/youtube.txt'

        def _apply_youtube_player_strategy(_url, opts):
            opts['cookiefile'] = 'D:/Code/init/squirrel/config/site_cookies/youtube.txt'
            opts['extractor_args']['youtube']['player_client'] = ['tv']

        support_module.apply_youtube_player_strategy = _apply_youtube_player_strategy
        module = _load_subtitles_module()
        provider = module.YoutubeSubtitlesProvider()

        content, filename = provider.get_subtitles(
            SimpleNamespace(id='demo', url='https://www.youtube.com/watch?v=demo'),
            'en',
            'srt',
        )

    assert content == '1\n00:00:00,000 --> 00:00:01,000\nhello\n'
    assert filename == 'demo.en.srt'
    assert len(calls) == 2
    assert calls[0]['cookiefile'] == 'D:/Code/init/squirrel/config/site_cookies/youtube.txt'
    assert calls[0]['extractor_args']['youtube']['player_client'] == ['tv']
    assert 'cookiefile' not in calls[1]
    assert calls[1]['extractor_args']['youtube']['player_client'] == ['android']


def test_youtube_subtitles_retry_after_bot_challenge(monkeypatch):
    calls = []

    class _FakeYoutubeDL:
        def __init__(self, opts):
            self.opts = dict(opts)

        def __enter__(self):
            calls.append(self.opts)
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def download(self, _urls):
            if len(calls) < 3:
                raise Exception("ERROR: [youtube] demo: Sign in to confirm you're not a bot")
            outdir = Path(self.opts['outtmpl']).parent
            (outdir / 'demo.en.srt').write_text('1\n00:00:00,000 --> 00:00:01,000\nhello\n', encoding='utf-8')

    with _stub_crawl_module(), _stub_yt_dlp_module(_FakeYoutubeDL), _stub_youtube_support_module():
        module = _load_subtitles_module()
        provider = module.YoutubeSubtitlesProvider()

        content, filename = provider.get_subtitles(
            SimpleNamespace(id='demo', url='https://www.youtube.com/watch?v=demo'),
            'en',
            'srt',
        )

    assert content == '1\n00:00:00,000 --> 00:00:01,000\nhello\n'
    assert filename == 'demo.en.srt'
    assert len(calls) == 3
    assert calls[0]['extractor_args']['youtube']['player_client'] == ['android']
    assert calls[1]['extractor_args']['youtube']['player_client'] == ['android']
    assert calls[2]['extractor_args']['youtube']['player_client'] == ['android']
