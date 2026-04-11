from __future__ import annotations

import importlib
import sys
import types
from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
from xml.etree import ElementTree as ET


ROOT = Path(__file__).resolve().parents[2]
BILIBILI_SRC = ROOT / 'squirrel-plugins' / 'bilibili' / 'src'


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
def _stub_bilibili_modules():
    originals = {
        name: sys.modules.get(name)
        for name in (
            'squirrel_bilibili',
            'squirrel_bilibili.sign',
            'squirrel_bilibili.handler',
            'squirrel_bilibili.mpd',
        )
    }

    package_module = types.ModuleType('squirrel_bilibili')
    package_module.__path__ = [str(BILIBILI_SRC / 'squirrel_bilibili')]  # type: ignore[attr-defined]

    sign_module = types.ModuleType('squirrel_bilibili.sign')
    sign_module.fetch_play_data = lambda *_args, **_kwargs: (_ for _ in ()).throw(
        AssertionError('network fetch should not run in this test')
    )

    try:
        sys.modules['squirrel_bilibili'] = package_module
        sys.modules['squirrel_bilibili.sign'] = sign_module
        sys.modules.pop('squirrel_bilibili.handler', None)
        sys.modules.pop('squirrel_bilibili.mpd', None)
        yield
    finally:
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


def test_bilibili_handler_keeps_quality_hints_across_codec_families(monkeypatch):
    with _stub_bilibili_modules(), _import_paths(BILIBILI_SRC):
        module = importlib.import_module('squirrel_bilibili.handler')

        monkeypatch.setattr(
            module,
            'get_dash_data',
            lambda _url: {
                'video': [
                    {
                        'id': 120,
                        'codecid': 13,
                        'codecs': 'av01.0.08M.08',
                        'width': 3840,
                        'height': 2160,
                        'bandwidth': 3200000,
                        'baseUrl': 'https://cdn.example.test/av1-2160.m4s',
                    },
                    {
                        'id': 80,
                        'codecid': 7,
                        'codecs': 'avc1.640028',
                        'width': 1920,
                        'height': 1080,
                        'bandwidth': 1800000,
                        'baseUrl': 'https://cdn.example.test/avc-1080.m4s',
                    },
                    {
                        'id': 64,
                        'codecid': 7,
                        'codecs': 'avc1.64001f',
                        'width': 1280,
                        'height': 720,
                        'bandwidth': 900000,
                        'baseUrl': 'https://cdn.example.test/avc-720.m4s',
                    },
                    {
                        'id': 112,
                        'codecid': 12,
                        'codecs': 'hev1.1.6.L123.B0',
                        'width': 1920,
                        'height': 1080,
                        'bandwidth': 2400000,
                        'baseUrl': 'https://cdn.example.test/hevc-1080.m4s',
                    },
                ],
                'audio': [
                    {
                        'id': 30216,
                        'codecs': 'mp4a.40.2',
                        'bandwidth': 192000,
                        'baseUrl': 'https://cdn.example.test/audio.m4s',
                    }
                ],
            },
        )

        payload = module.BilibiliHandler().get_video_url(
            SimpleNamespace(id=123, url='https://www.bilibili.com/video/BV-demo')
        )

        assert payload['mpd_url'] == '/api/video/mpd?video_id=123'
        assert 'https%3A//cdn.example.test/av1-2160.m4s' in payload['video_url']

        qualities_by_id = {
            item['id']: item
            for item in payload['qualities']
        }
        assert set(qualities_by_id) == {'120', '112', '80', '64'}
        assert qualities_by_id['120']['codec'] == 'av1'
        assert qualities_by_id['112']['codec'] == 'hevc'
        assert qualities_by_id['80']['codec'] == 'avc'
        assert qualities_by_id['64']['codec'] == 'avc'
        assert qualities_by_id['120']['index'] == 0
        assert qualities_by_id['112']['index'] == 0
        assert qualities_by_id['80']['index'] == 0
        assert qualities_by_id['64']['index'] == 1


def test_bilibili_mpd_builder_splits_video_adaptation_sets_by_codec_family(monkeypatch):
    with _stub_bilibili_modules(), _import_paths(BILIBILI_SRC):
        module = importlib.import_module('squirrel_bilibili.mpd')

        monkeypatch.setattr(
            module,
            'get_dash_data',
            lambda _url: {
                'duration': 120,
                'minBufferTime': 1.5,
                'video': [
                    {
                        'id': 120,
                        'codecid': 13,
                        'codecs': 'av01.0.08M.08',
                        'width': 3840,
                        'height': 2160,
                        'bandwidth': 4200000,
                        'baseUrl': 'https://cdn.example.test/av1-2160.m4s',
                        'SegmentBase': {
                            'indexRange': '100-200',
                            'Initialization': '0-99',
                        },
                    },
                    {
                        'id': 116,
                        'codecid': 13,
                        'codecs': 'av01.0.05M.08',
                        'width': 1920,
                        'height': 1080,
                        'bandwidth': 1900000,
                        'baseUrl': 'https://cdn.example.test/av1-1080.m4s',
                        'SegmentBase': {
                            'indexRange': '100-200',
                            'Initialization': '0-99',
                        },
                    },
                    {
                        'id': 112,
                        'codecid': 12,
                        'codecs': 'hev1.1.6.L123.B0',
                        'width': 1920,
                        'height': 1080,
                        'bandwidth': 2600000,
                        'baseUrl': 'https://cdn.example.test/hevc-1080.m4s',
                        'SegmentBase': {
                            'indexRange': '100-200',
                            'Initialization': '0-99',
                        },
                    },
                    {
                        'id': 64,
                        'codecid': 12,
                        'codecs': 'hev1.1.6.L120.B0',
                        'width': 1280,
                        'height': 720,
                        'bandwidth': 1200000,
                        'baseUrl': 'https://cdn.example.test/hevc-720.m4s',
                        'SegmentBase': {
                            'indexRange': '100-200',
                            'Initialization': '0-99',
                        },
                    },
                ],
                'audio': [
                    {
                        'id': 30216,
                        'codecs': 'mp4a.40.2',
                        'bandwidth': 192000,
                        'baseUrl': 'https://cdn.example.test/audio.m4s',
                        'SegmentBase': {
                            'indexRange': '100-200',
                            'Initialization': '0-99',
                        },
                    }
                ],
            },
        )

        xml = module.BilibiliMpdBuilder().build_mpd(
            SimpleNamespace(id=123, url='https://www.bilibili.com/video/BV-demo')
        )

        root = ET.fromstring(xml)
        ns = {'mpd': 'urn:mpeg:dash:schema:mpd:2011'}
        video_sets = root.findall('./mpd:Period/mpd:AdaptationSet[@contentType="video"]', ns)

        assert len(video_sets) == 2

        def codec_families_for_set(adaptation_set) -> set[str]:
            families = set()
            for representation in adaptation_set.findall('./mpd:Representation', ns):
                codecs = (representation.get('codecs') or '').lower()
                if 'av01' in codecs or 'av1' in codecs:
                    families.add('av1')
                elif 'hev1' in codecs or 'hvc1' in codecs or 'hevc' in codecs or 'h265' in codecs:
                    families.add('hevc')
            return families

        codec_families = [codec_families_for_set(adaptation_set) for adaptation_set in video_sets]
        assert {'av1'} in codec_families
        assert {'hevc'} in codec_families
        assert all(len(families) == 1 for families in codec_families)
