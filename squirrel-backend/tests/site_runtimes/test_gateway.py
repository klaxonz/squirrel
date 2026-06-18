import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import RuntimeErrorCode, SiteRuntimeInvokeResponse

from infrastructure.site_runtimes.gateway import SiteRuntimeGateway
from infrastructure.site_runtimes.models import SiteRuntimeCapability, SiteRuntimeManifest, SiteRuntimeSite


class _RecordingInvocationClient:
    def __init__(self) -> None:
        self.last_request = None
        self.last_target = None

    def invoke(self, target, request):
        self.last_target = target
        self.last_request = request
        return SiteRuntimeInvokeResponse(request_id=request.request_id, ok=True, data={"ok": True})


def test_gateway_uses_manifest_capability_timeout_when_request_timeout_is_omitted():
    client = _RecordingInvocationClient()
    gateway = SiteRuntimeGateway(invocation_client=client)
    gateway.register_manifest(
        runtime_id="javdb",
        version="0.1.0",
        manifest=SiteRuntimeManifest(
            runtime_id="javdb",
            version="0.1.0",
            capabilities=[
                SiteRuntimeCapability(name="check_login_status", timeout_ms=30000),
            ],
            sites=[
                SiteRuntimeSite(site_name="javdb", domains=["javdb.com"]),
            ],
        ),
    )

    response = gateway.invoke("check_login_status", site_name="javdb")

    assert response.ok is True
    assert client.last_request is not None
    assert client.last_request.timeout_ms == 30000


def test_gateway_returns_stable_error_code_for_route_miss():
    gateway = SiteRuntimeGateway(invocation_client=_RecordingInvocationClient())

    response = gateway.invoke("fetch_subtitles", domain="example.com")

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == RuntimeErrorCode.ROUTE_NOT_FOUND
    assert response.error.details == {
        "capability": "fetch_subtitles",
        "site_name": None,
        "domain": "example.com",
    }

