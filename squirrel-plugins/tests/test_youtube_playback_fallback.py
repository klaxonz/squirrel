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
def _stub_handler_dependencies():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'crawl',
            'squirrel_youtube',
            'squirrel_youtube.mpd',
            'squirrel_youtube.playback_mapper',
            'squirrel_youtube.youtubei_resolver',
        )
    }

    crawl_module = types.ModuleType('crawl')

    class ParseError(Exception):
        pass

    class VideoUrlHandler:
        pass

    crawl_module.ParseError = ParseError
    crawl_module.VideoUrlHandler = VideoUrlHandler
    crawl_module.filter_cookies_to_query_string = lambda _url: ''

    mpd_module = types.ModuleType('squirrel_youtube.mpd')
    mpd_module._build_dash_representations = lambda _info: []
    mpd_module._extract_video_info = lambda _url: None
    mpd_module._proxy = lambda url, referer=None: url

    package_module = types.ModuleType('squirrel_youtube')
    package_module.__path__ = [str(YOUTUBE_SRC / 'squirrel_youtube')]  # type: ignore[attr-defined]

    playback_mapper_module = types.ModuleType('squirrel_youtube.playback_mapper')
    playback_mapper_module.map_youtubei_result = lambda _video_id, _result: {'video_url': 'https://mapped.test'}

    youtubei_resolver_module = types.ModuleType('squirrel_youtube.youtubei_resolver')
    youtubei_resolver_module.resolve_with_youtubei = lambda _video_id: None

    try:
        sys.modules['crawl'] = crawl_module
        sys.modules['squirrel_youtube'] = package_module
        sys.modules['squirrel_youtube.mpd'] = mpd_module
        sys.modules['squirrel_youtube.playback_mapper'] = playback_mapper_module
        sys.modules['squirrel_youtube.youtubei_resolver'] = youtubei_resolver_module
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_handler_falls_back_when_youtubei_primary_is_incomplete(monkeypatch):
    with _stub_handler_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.handler')
        handler = module.YouTubeHandler()
        video = SimpleNamespace(id=123, url='https://www.youtube.com/watch?v=demo')

        monkeypatch.setattr(
            module,
            'resolve_with_youtubei',
            lambda _video_id: (_ for _ in ()).throw(ValueError('incomplete result')),
        )
        monkeypatch.setattr(
            handler,
            '_build_legacy_playback_payload',
            lambda _video: {
                'video_url': 'https://fallback.test/video.mp4',
                'audio_url': None,
                'mpd_url': None,
                'qualities': None,
            },
        )

        payload = handler.get_video_url(video)

        assert payload['video_url'] == 'https://fallback.test/video.mp4'


def test_handler_uses_watch_id_instead_of_database_id(monkeypatch):
    with _stub_handler_dependencies(), _import_paths(YOUTUBE_SRC):
        module = importlib.import_module('squirrel_youtube.handler')
        handler = module.YouTubeHandler()
        video = SimpleNamespace(id=123, url='https://www.youtube.com/watch?v=z0NnBVMqo64')
        captured = {}

        monkeypatch.setattr(
            module,
            'resolve_with_youtubei',
            lambda video_id: captured.setdefault('video_id', video_id) or (_ for _ in ()).throw(ValueError('stop')),
        )
        monkeypatch.setattr(handler, '_build_legacy_playback_payload', lambda _video: None)

        try:
            handler.get_video_url(video)
        except Exception:
            pass

        assert captured['video_id'] == 'z0NnBVMqo64'
