from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from services.subscription_update.models import SubscriptionUpdateRequest, UpdateMode, UpdateTrigger
from services.subscription_update.strategies.default_strategy import DefaultUpdateStrategy


def test_fetch_videos_uses_plugin_gateway_sync_subscription(monkeypatch):
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
                request_id='sync-1',
                ok=True,
                data={
                    'video_urls': ['https://www.bilibili.com/video/BV1xx411c7mD'],
                    'latest_video_url': 'https://www.bilibili.com/video/BV1xx411c7mD',
                    'cursor_payload': {'latest_video_url': 'https://www.bilibili.com/video/BV1xx411c7mD'},
                    'stop_reason': 'source_exhausted',
                    'total_available': 1,
                },
            )

    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.get_plugin_manager',
        lambda: SimpleNamespace(gateway=_FakeGateway()),
    )
    monkeypatch.setattr(
        'services.subscription_update.strategies.default_strategy.SiteCatalog.find_site_by_domain',
        lambda domain: ('bilibili', {'domains': ['bilibili.com']}),
    )

    request = SubscriptionUpdateRequest(
        subscription_id=1,
        url='https://space.bilibili.com/42',
        trigger=UpdateTrigger.MANUAL,
        mode=UpdateMode.INCREMENTAL,
        cursor_payload={'cursor': '1'},
        last_seen_video_url='https://www.bilibili.com/video/OLD',
    )

    result = DefaultUpdateStrategy().fetch_videos(request)

    assert calls == [{
        'capability': 'sync_subscription',
        'payload': {
            'url': 'https://space.bilibili.com/42',
            'mode': 'incremental',
            'cursor_payload': {'cursor': '1'},
            'last_seen_video_url': 'https://www.bilibili.com/video/OLD',
            'limit': 30,
        },
        'site_name': 'bilibili',
        'domain': 'space.bilibili.com',
        'timeout_ms': None,
    }]
    assert result.video_urls == ['https://www.bilibili.com/video/BV1xx411c7mD']
    assert result.latest_video_url == 'https://www.bilibili.com/video/BV1xx411c7mD'
    assert result.total_available == 1
