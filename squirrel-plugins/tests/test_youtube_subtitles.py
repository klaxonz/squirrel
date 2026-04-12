from __future__ import annotations

import importlib.util
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[2]
YOUTUBE_SRC = ROOT / 'squirrel-plugins' / 'youtube' / 'src'
YOUTUBE_PACKAGE = YOUTUBE_SRC / 'squirrel_youtube'
SUBTITLES_PATH = YOUTUBE_PACKAGE / 'subtitles.py'


@contextmanager
def _stub_crawl_module():
    original = sys.modules.get('crawl')
    crawl_module = types.ModuleType('crawl')
    crawl_module.SubtitlesProvider = object
    try:
        sys.modules['crawl'] = crawl_module
        yield crawl_module
    finally:
        if original is None:
            sys.modules.pop('crawl', None)
        else:
            sys.modules['crawl'] = original


@contextmanager
def _stub_youtube_modules():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'squirrel_youtube',
            'squirrel_youtube.video_id',
            'squirrel_youtube.youtubei_resolver',
        )
    }

    package_module = types.ModuleType('squirrel_youtube')
    package_module.__path__ = [str(YOUTUBE_PACKAGE)]

    video_id_module = types.ModuleType('squirrel_youtube.video_id')
    video_id_module.extract_youtube_video_id = lambda _url: 'demo-video'

    resolver_module = types.ModuleType('squirrel_youtube.youtubei_resolver')
    resolver_module.resolve_captions_with_youtubei = lambda _video_id, _lang: {
        'content': '',
        'language_code': 'en',
    }

    try:
        sys.modules['squirrel_youtube'] = package_module
        sys.modules['squirrel_youtube.video_id'] = video_id_module
        sys.modules['squirrel_youtube.youtubei_resolver'] = resolver_module
        yield video_id_module, resolver_module
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def _load_subtitles_module():
    module_name = 'squirrel_youtube.subtitles'
    sys.modules.pop(module_name, None)
    module_spec = importlib.util.spec_from_file_location(module_name, SUBTITLES_PATH)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec is not None and module_spec.loader is not None
    sys.modules[module_name] = module
    module_spec.loader.exec_module(module)
    return module


def test_youtube_subtitles_provider_converts_srv3_xml_to_srt():
    srv3_xml = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<timedtext format="3"><body>'
        '<p t="1000" d="1500">Hello</p>'
        '<p t="3000"><s>World</s><s>!</s></p>'
        '</body></timedtext>'
    )

    with _stub_crawl_module(), _stub_youtube_modules() as (_video_id_module, resolver_module):
        resolver_module.resolve_captions_with_youtubei = lambda _video_id, _lang: {
            'content': srv3_xml,
            'language_code': 'en',
        }
        module = _load_subtitles_module()
        provider = module.YoutubeSubtitlesProvider()

        content, filename = provider.get_subtitles(
            SimpleNamespace(id='db-id', url='https://www.youtube.com/watch?v=demo-video'),
            'en',
            'srt',
        )

    assert content == (
        '1\n'
        '00:00:01,000 --> 00:00:02,500\n'
        'Hello\n'
        '\n'
        '2\n'
        '00:00:03,000 --> 00:00:05,000\n'
        'World!\n'
    )
    assert filename == 'demo-video.en.srt'


def test_youtube_subtitles_provider_uses_resolved_language_code_in_filename():
    srv3_xml = (
        '<?xml version="1.0" encoding="utf-8" ?>'
        '<timedtext format="3"><body>'
        '<p t="0" d="1000">Hello</p>'
        '</body></timedtext>'
    )

    with _stub_crawl_module(), _stub_youtube_modules() as (_video_id_module, resolver_module):
        resolver_module.resolve_captions_with_youtubei = lambda _video_id, _lang: {
            'content': srv3_xml,
            'language_code': 'en',
        }
        module = _load_subtitles_module()
        provider = module.YoutubeSubtitlesProvider()

        _content, filename = provider.get_subtitles(
            SimpleNamespace(id='db-id', url='https://www.youtube.com/watch?v=demo-video'),
            'en-US',
            'srt',
        )

    assert filename == 'demo-video.en.srt'


def test_youtube_subtitles_provider_surfaces_worker_errors():
    with _stub_crawl_module(), _stub_youtube_modules() as (_video_id_module, resolver_module):
        resolver_module.resolve_captions_with_youtubei = lambda _video_id, _lang: (_ for _ in ()).throw(
            ValueError('No subtitles available: worker failed')
        )
        module = _load_subtitles_module()
        provider = module.YoutubeSubtitlesProvider()

        with pytest.raises(ValueError, match='No subtitles available'):
            provider.get_subtitles(
                SimpleNamespace(id='db-id', url='https://www.youtube.com/watch?v=demo-video'),
                'en',
                'srt',
            )


def test_youtube_subtitles_provider_rejects_non_srt_formats():
    with _stub_crawl_module(), _stub_youtube_modules():
        module = _load_subtitles_module()
        provider = module.YoutubeSubtitlesProvider()

        with pytest.raises(ValueError, match='Only srt format is supported'):
            provider.get_subtitles(
                SimpleNamespace(id='db-id', url='https://www.youtube.com/watch?v=demo-video'),
                'en',
                'vtt',
            )
