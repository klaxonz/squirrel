from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import url_helper


def test_get_site_from_url_reads_runtime_registrations(monkeypatch):
    registrations = [
        SimpleNamespace(
            capability='extract_video',
            site_name='youtube',
            domains=['youtube.com', 'youtu.be'],
        ),
        SimpleNamespace(
            capability='resolve_playback',
            site_name='bilibili',
            domains=['bilibili.com', 'b23.tv'],
        ),
    ]

    monkeypatch.setattr(
        url_helper,
        'get_plugin_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(registrations=registrations),
        ),
        raising=False,
    )

    assert url_helper.get_site_from_url('https://www.youtube.com/watch?v=demo') == 'youtube'
    assert url_helper.get_site_from_url('https://m.bilibili.com/video/BV1xx411c7mD') == 'bilibili'


def test_get_site_from_url_returns_none_when_no_runtime_route(monkeypatch):
    monkeypatch.setattr(
        url_helper,
        'get_plugin_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(registrations=[]),
        ),
        raising=False,
    )

    assert url_helper.get_site_from_url('https://example.com/video/1') is None
