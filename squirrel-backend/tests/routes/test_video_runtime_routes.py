import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from routes import video as video_route


def test_get_video_subtitles_reads_from_plugin_gateway(monkeypatch):
    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='subtitles-1',
                ok=True,
                data={
                    'content': '1\n00:00:00,000 --> 00:00:01,000\nhello\n',
                    'filename': 'BV1xx411c7mD.ai-zh.srt',
                    'media_type': 'text/plain; charset=utf-8',
                },
            )

    monkeypatch.setattr(
        video_route.video_service,
        'get_video_by_id',
        lambda video_id: SimpleNamespace(
            id=video_id,
            url='https://www.bilibili.com/video/BV1xx411c7mD',
            title='Test video',
            duration=120,
        ),
    )
    monkeypatch.setattr(
        video_route,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
        raising=False,
    )

    response = video_route.get_video_subtitles(
        video_id=1,
        lang='ai-zh',
        fmt='srt',
        current_user=SimpleNamespace(id=1),
    )

    assert calls == [{
        'capability': 'fetch_subtitles',
        'payload': {
            'video_id': 1,
            'url': 'https://www.bilibili.com/video/BV1xx411c7mD',
            'title': 'Test video',
            'duration': 120,
            'lang': 'ai-zh',
            'fmt': 'srt',
        },
        'site_name': None,
        'domain': 'bilibili.com',
        'timeout_ms': None,
    }]
    assert response.body.decode('utf-8') == '1\n00:00:00,000 --> 00:00:01,000\nhello\n'
    assert response.headers['content-disposition'] == 'inline; filename="BV1xx411c7mD.ai-zh.srt"'


def test_get_video_mpd_reads_from_plugin_gateway(monkeypatch):
    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='mpd-1',
                ok=True,
                data={
                    'content': '<MPD></MPD>',
                    'media_type': 'application/dash+xml',
                },
            )

    monkeypatch.setattr(
        video_route.video_service,
        'get_video_by_id',
        lambda video_id: SimpleNamespace(
            id=video_id,
            url='https://www.youtube.com/watch?v=demo',
            title='Runtime video',
            duration=120,
        ),
    )
    monkeypatch.setattr(
        video_route,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
        raising=False,
    )

    response = video_route.get_video_mpd(video_id=1)

    assert calls == [{
        'capability': 'build_mpd',
        'payload': {
            'video_id': 1,
            'url': 'https://www.youtube.com/watch?v=demo',
            'title': 'Runtime video',
            'duration': 120,
        },
        'site_name': None,
        'domain': 'youtube.com',
        'timeout_ms': None,
    }]
    assert response.body.decode('utf-8') == '<MPD></MPD>'
    assert response.media_type == 'application/dash+xml'


def test_get_video_mpd_passes_direct_playback_flag(monkeypatch):
    calls = []

    class _FakeGateway:
        def invoke(self, capability, payload=None, site_name=None, domain=None, timeout_ms=None):
            calls.append({
                'capability': capability,
                'payload': payload,
                'site_name': site_name,
                'domain': domain,
                'timeout_ms': timeout_ms,
            })
            return PluginInvokeResponse(
                request_id='mpd-1',
                ok=True,
                data={
                    'content': '<MPD></MPD>',
                    'media_type': 'application/dash+xml',
                },
            )

    monkeypatch.setattr(
        video_route.video_service,
        'get_video_by_id',
        lambda video_id: SimpleNamespace(
            id=video_id,
            url='https://www.youtube.com/watch?v=demo',
            title='Runtime video',
            duration=120,
        ),
    )
    monkeypatch.setattr(
        video_route,
        'get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
        raising=False,
    )

    response = video_route.get_video_mpd(video_id=1, direct=True)

    assert calls == [{
        'capability': 'build_mpd',
        'payload': {
            'video_id': 1,
            'url': 'https://www.youtube.com/watch?v=demo',
            'title': 'Runtime video',
            'duration': 120,
            'direct_playback': True,
        },
        'site_name': None,
        'domain': 'youtube.com',
        'timeout_ms': None,
    }]
    assert response.body.decode('utf-8') == '<MPD></MPD>'
