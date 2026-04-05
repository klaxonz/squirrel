from __future__ import annotations

import importlib
import sys
import types
from contextlib import contextmanager
from pathlib import Path


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
def _stub_crawl_module():
    original = sys.modules.get('crawl')
    crawl_module = types.ModuleType('crawl')
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


def test_ytdlp_support_prefers_bundled_bgutil_server_home():
    with _stub_crawl_module(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.ytdlp_support')
        server_home = module._resolve_bgutil_server_home()

        assert server_home == module.LOCAL_BGUTIL_SERVER_HOME
        assert (server_home / 'build' / 'generate_once.js').is_file()


def test_apply_youtube_player_strategy_uses_bundled_pot_provider_for_authenticated_requests(monkeypatch):
    with _stub_crawl_module(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.ytdlp_support')
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
