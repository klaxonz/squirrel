from __future__ import annotations

import json
import sys
import threading
import time
import types
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'squirrel-plugins' / 'youtube' / 'src'))

import squirrel_youtube.youtubei_resolver as resolver_module
from squirrel_youtube.youtubei_resolver import parse_worker_payload, resolve_with_youtubei


def _reset_worker_state() -> None:
    resolver_module._RESULT_CACHE.clear()
    resolver_module._WORKER_CLIENT = None
    resolver_module._PREWARM_THREAD = None


def test_parse_worker_payload_accepts_complete_android_result():
    payload = {
        'status': 'ok',
        'client': 'ANDROID',
        'playability_status': 'OK',
        'formats': [
            {
                'itag': 18,
                'mime_type': 'video/mp4; codecs="avc1.42001E, mp4a.40.2"',
                'quality_label': '360p',
                'url': 'https://example.test/itag/18',
                'has_audio': True,
                'has_video': True,
            },
            {
                'itag': 137,
                'mime_type': 'video/mp4; codecs="avc1.640028"',
                'quality_label': '1080p',
                'url': 'https://example.test/itag/137',
                'has_audio': False,
                'has_video': True,
            },
        ],
    }

    result = parse_worker_payload(json.dumps(payload))

    assert result.client == 'ANDROID'
    assert result.playability_status == 'OK'
    assert len(result.formats) == 2


def test_parse_worker_payload_rejects_empty_format_set():
    payload = json.dumps({
        'status': 'ok',
        'client': 'ANDROID',
        'playability_status': 'OK',
        'formats': [],
    })

    with pytest.raises(ValueError, match='complete format set'):
        parse_worker_payload(payload)


def test_resolve_with_youtubei_passes_cookie_to_worker(monkeypatch):
    _reset_worker_state()
    captured = {}

    crawl_module = types.ModuleType('crawl')
    crawl_module.filter_cookies_to_query_string = lambda _url: 'SAPISID=abc; SID=def'
    monkeypatch.setitem(sys.modules, 'crawl', crawl_module)

    class FakeWorkerClient:
        def request(self, payload, timeout_seconds):
            captured['input'] = payload
            captured['timeout_seconds'] = timeout_seconds
            return json.dumps({
            'status': 'ok',
            'client': 'MWEB',
            'playability_status': 'OK',
            'formats': [
                {
                    'itag': 18,
                    'mime_type': 'video/mp4; codecs="avc1.42001E, mp4a.40.2"',
                    'quality_label': '360p',
                    'url': 'https://example.test/itag/18',
                    'has_audio': True,
                    'has_video': True,
                }
            ],
        })

    monkeypatch.setattr(resolver_module, '_get_worker_client', lambda: FakeWorkerClient())

    result = resolve_with_youtubei('demo-video', timeout_seconds=1)

    assert result.client == 'MWEB'
    assert captured['input']['video_id'] == 'demo-video'
    assert captured['input']['cookie'] == 'SAPISID=abc; SID=def'
    assert captured['timeout_seconds'] == 1


def test_cache_key_changes_when_cookie_auth_is_present():
    assert resolver_module._cache_key('demo', '') != resolver_module._cache_key('demo', 'SAPISID=abc')


def test_worker_timeout_keeps_headroom_for_authenticated_cold_starts():
    assert resolver_module.WORKER_TIMEOUT_SECONDS >= 20.0


def test_resolve_with_youtubei_returns_worker_result_without_media_probe(monkeypatch):
    _reset_worker_state()

    crawl_module = types.ModuleType('crawl')
    crawl_module.filter_cookies_to_query_string = lambda _url: 'SAPISID=abc; SID=def'
    monkeypatch.setitem(sys.modules, 'crawl', crawl_module)

    class FakeWorkerClient:
        def request(self, payload, timeout_seconds):
            return json.dumps({
            'status': 'ok',
            'client': 'MWEB',
            'playability_status': 'OK',
            'formats': [
                {
                    'itag': 18,
                    'mime_type': 'video/mp4; codecs="avc1.42001E, mp4a.40.2"',
                    'quality_label': '360p',
                    'url': 'https://example.test/itag/18',
                    'has_audio': True,
                    'has_video': True,
                }
            ],
        })

    monkeypatch.setattr(resolver_module, '_get_worker_client', lambda: FakeWorkerClient())

    result = resolve_with_youtubei('demo-video', timeout_seconds=1)

    assert result.client == 'MWEB'
    assert result.formats[0].url == 'https://example.test/itag/18'


def test_get_worker_client_reuses_singleton(monkeypatch):
    _reset_worker_state()
    created = []

    class FakeClient:
        def __init__(self):
            created.append(object())

    monkeypatch.setattr(resolver_module, '_YoutubeiWorkerClient', FakeClient)

    first = resolver_module._get_worker_client()
    second = resolver_module._get_worker_client()

    assert first is second
    assert len(created) == 1


def test_shutdown_youtubei_worker_tolerates_clients_without_close():
    _reset_worker_state()
    resolver_module._WORKER_CLIENT = object()

    resolver_module.shutdown_youtubei_worker()

    assert resolver_module._WORKER_CLIENT is None


def test_prewarm_youtubei_worker_runs_in_background(monkeypatch):
    _reset_worker_state()
    started = threading.Event()
    release = threading.Event()

    class FakeWorkerClient:
        def prewarm(self, cookie_header=''):
            assert cookie_header == 'SAPISID=abc'
            started.set()
            release.wait(timeout=1)

    monkeypatch.setattr(resolver_module, '_get_worker_client', lambda: FakeWorkerClient())
    monkeypatch.setattr(resolver_module, '_load_cookie_header_for_target', lambda _url: 'SAPISID=abc')

    started_at = time.monotonic()
    resolver_module.prewarm_youtubei_worker()
    elapsed = time.monotonic() - started_at

    assert elapsed < 0.2
    assert started.wait(timeout=0.2)

    release.set()
    deadline = time.monotonic() + 1
    while resolver_module._PREWARM_THREAD is not None and time.monotonic() < deadline:
        time.sleep(0.01)

    assert resolver_module._PREWARM_THREAD is None


def test_prewarm_youtubei_worker_deduplicates_inflight_thread(monkeypatch):
    _reset_worker_state()
    started = threading.Event()
    release = threading.Event()
    calls: list[str] = []

    class FakeWorkerClient:
        def prewarm(self, cookie_header=''):
            calls.append(cookie_header)
            started.set()
            release.wait(timeout=1)

    monkeypatch.setattr(resolver_module, '_get_worker_client', lambda: FakeWorkerClient())
    monkeypatch.setattr(resolver_module, '_load_cookie_header_for_target', lambda _url: 'SAPISID=abc')

    resolver_module.prewarm_youtubei_worker()
    assert started.wait(timeout=0.2)
    resolver_module.prewarm_youtubei_worker()

    release.set()
    deadline = time.monotonic() + 1
    while resolver_module._PREWARM_THREAD is not None and time.monotonic() < deadline:
        time.sleep(0.01)

    assert calls == ['SAPISID=abc']
