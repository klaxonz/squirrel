from __future__ import annotations

import importlib
import sys
import tempfile
import types
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
YOUTUBE_SRC = ROOT / 'squirrel-site-runtimes' / 'youtube' / 'src'
YTDLP_SUPPORT_PATH = YOUTUBE_SRC / 'squirrel_youtube' / 'ytdlp_support.py'


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
def _stub_crawl_module():
    original = sys.modules.get('crawl')
    import crawl as real_crawl

    crawl_module = types.ModuleType('crawl')
    crawl_module.__dict__.update(real_crawl.__dict__)
    crawl_module.filter_cookies_to_query_string = lambda _url: ''
    crawl_module.resolve_cookie_file_path = lambda _url: None
    try:
        sys.modules['crawl'] = crawl_module
        yield crawl_module
    finally:
        if original is None:
            sys.modules.pop('crawl', None)
        else:
            sys.modules['crawl'] = original


def _load_ytdlp_support_module():
    module_name = '_test_squirrel_youtube_ytdlp_support'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, YTDLP_SUPPORT_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


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


def test_ytdlp_support_prefers_bundled_bgutil_server_home():
    with _stub_crawl_module(), _import_paths(YOUTUBE_SRC):
        module = _load_ytdlp_support_module()
        server_home = module._resolve_bgutil_server_home()

        assert server_home == module.LOCAL_BGUTIL_SERVER_HOME
        assert (server_home / 'build' / 'generate_once.js').is_file()


def test_ytdlp_support_does_not_fallback_to_home_bgutil_server(tmp_path, monkeypatch):
    with _stub_crawl_module(), _import_paths(YOUTUBE_SRC):
        module = _load_ytdlp_support_module()
        bundled_server_home = tmp_path / 'bundled-node'

        monkeypatch.delenv(module.YOUTUBE_POT_PROVIDER_SERVER_HOME_ENV, raising=False)
        monkeypatch.setattr(module, 'LOCAL_BGUTIL_SERVER_HOME', bundled_server_home)

        server_home = module._resolve_bgutil_server_home()

        assert server_home == bundled_server_home


def test_apply_youtube_player_strategy_uses_bundled_pot_provider_for_authenticated_requests(monkeypatch):
    with _stub_crawl_module(), _import_paths(YOUTUBE_SRC):
        module = _load_ytdlp_support_module()
        opts = {}

        monkeypatch.setattr(module, 'apply_youtube_auth', lambda _url, _opts: True)
        monkeypatch.setattr(
            module,
            '_resolve_pot_provider_args',
            lambda: (
                'youtubepot-bgutilscript',
                {'server_home': [str(module.LOCAL_BGUTIL_SERVER_HOME)]},
            ),
        )

        module.apply_youtube_player_strategy('https://www.youtube.com/watch?v=demo', opts)

        assert opts['extractor_args']['youtube']['player_client'] == ['mweb']
        assert opts['extractor_args']['youtubepot-bgutilscript']['server_home'] == [
            str(module.LOCAL_BGUTIL_SERVER_HOME)
        ]


def test_extract_info_uses_temporary_cookiefile_copy():
    calls: list[dict] = []

    class _FakeYoutubeDL:
        def __init__(self, opts):
            self.opts = dict(opts)

        def __enter__(self):
            calls.append(self.opts)
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def extract_info(self, _url, download=False, process=True):
            Path(self.opts['cookiefile']).write_text('mutated-by-ytdlp', encoding='utf-8')
            return {'id': 'demo', 'download': download, 'process': process}

    with tempfile.TemporaryDirectory() as temp_dir:
        original_cookie_path = Path(temp_dir) / 'youtube.txt'
        original_cookie_path.write_text('original-cookie', encoding='utf-8')

        with _stub_crawl_module(), _stub_yt_dlp_module(_FakeYoutubeDL), _import_paths(YOUTUBE_SRC):
            module = _load_ytdlp_support_module()
            info = module.extract_info(
                'https://www.youtube.com/watch?v=demo',
                {'cookiefile': str(original_cookie_path)},
                process=False,
            )

        assert info == {'id': 'demo', 'download': False, 'process': False}
        assert len(calls) == 1
        assert calls[0]['cookiefile'] != str(original_cookie_path)
        assert original_cookie_path.read_text(encoding='utf-8') == 'original-cookie'
