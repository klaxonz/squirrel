from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeResponse
from site_runtimes.gateway import SiteRuntimeGateway
from site_runtimes.runtime_models import PluginCapability, PluginManifest, PluginSiteManifest


class _RecordingInvocationClient:
    def __init__(self) -> None:
        self.last_request = None
        self.last_target = None

    def invoke(self, target, request):
        self.last_target = target
        self.last_request = request
        return PluginInvokeResponse(request_id=request.request_id, ok=True, data={'ok': True})


def test_gateway_uses_manifest_capability_timeout_when_request_timeout_is_omitted():
    client = _RecordingInvocationClient()
    gateway = SiteRuntimeGateway(invocation_client=client)
    gateway.register_manifest(
        plugin_id='javdb',
        version='0.1.0',
        manifest=PluginManifest(
            plugin_id='javdb',
            version='0.1.0',
            capabilities=[
                PluginCapability(name='check_login_status', timeout_ms=30000),
            ],
            sites=[
                PluginSiteManifest(site_name='javdb', domains=['javdb.com']),
            ],
        ),
    )

    response = gateway.invoke('check_login_status', site_name='javdb')

    assert response.ok is True
    assert client.last_request is not None
    assert client.last_request.timeout_ms == 30000


def test_gateway_refreshes_registrations_once_before_returning_route_miss():
    client = _RecordingInvocationClient()
    refresh_calls = []
    gateway = SiteRuntimeGateway(invocation_client=client)

    def _refresh():
        refresh_calls.append('called')
        gateway.register_manifest(
            plugin_id='youporn',
            version='0.1.0',
            manifest=PluginManifest(
                plugin_id='youporn',
                version='0.1.0',
                capabilities=[
                    PluginCapability(name='resolve_subscription', timeout_ms=30000),
                ],
                sites=[
                    PluginSiteManifest(site_name='youporn', domains=['youporn.com']),
                ],
            ),
        )

    gateway.set_registration_refresh(_refresh)

    response = gateway.invoke('resolve_subscription', domain='youporn.com')

    assert response.ok is True
    assert refresh_calls == ['called']
    assert client.last_target is not None
    assert client.last_target.plugin_id == 'youporn'


