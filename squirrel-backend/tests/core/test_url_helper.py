from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from utils import url_helper


def test_get_site_from_url_reads_runtime_registrations(monkeypatch):
    url_helper.reset_site_lookup_cache()
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
    url_helper.reset_site_lookup_cache()
    monkeypatch.setattr(
        url_helper,
        'get_plugin_manager',
        lambda: SimpleNamespace(
            get_snapshot=lambda: SimpleNamespace(registrations=[]),
        ),
        raising=False,
    )

    assert url_helper.get_site_from_url('https://example.com/video/1') is None


def test_get_site_from_url_reuses_cached_registration_index(monkeypatch):
    url_helper.reset_site_lookup_cache()
    snapshot_calls = {'count': 0}
    registrations = [
        SimpleNamespace(
            capability='extract_video',
            site_name='youtube',
            domains=['youtube.com', 'youtu.be'],
        ),
    ]

    def _get_snapshot():
        snapshot_calls['count'] += 1
        return SimpleNamespace(registrations=registrations)

    monkeypatch.setattr(
        url_helper,
        'get_plugin_manager',
        lambda: SimpleNamespace(get_snapshot=_get_snapshot),
        raising=False,
    )

    assert url_helper.get_site_from_url('https://www.youtube.com/watch?v=demo') == 'youtube'
    assert url_helper.get_site_from_url('https://m.youtube.com/watch?v=demo2') == 'youtube'
    assert snapshot_calls['count'] == 1
