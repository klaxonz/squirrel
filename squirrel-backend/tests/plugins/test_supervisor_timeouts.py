from pathlib import Path
import socket
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeRequest
from crawl.runtime_errors import RuntimeErrorCode
from plugins.models import PluginHealthSnapshot, PluginRoutingTarget, PluginRuntimeHandle, PluginRuntimeState
from plugins.supervisor import PluginRuntimeSupervisor


def test_supervisor_returns_timeout_error_when_runtime_request_times_out(monkeypatch):
    supervisor = PluginRuntimeSupervisor()
    supervisor._handles['javdb:0.1.0'] = PluginRuntimeHandle(
        plugin_id='javdb',
        version='0.1.0',
        state=PluginRuntimeState.RUNNING,
        endpoint='http://127.0.0.1:65535',
        health=PluginHealthSnapshot(plugin_id='javdb', healthy=True, status='running'),
    )

    def _raise_timeout(*_args, **_kwargs):
        raise socket.timeout('timed out')

    monkeypatch.setattr(supervisor, '_request_json', _raise_timeout)

    response = supervisor.invoke(
        PluginRoutingTarget(
            plugin_id='javdb',
            version='0.1.0',
            capability='check_login_status',
            site_name='javdb',
        ),
        PluginInvokeRequest(
            request_id='req-1',
            capability='check_login_status',
            payload={},
            site_name='javdb',
            timeout_ms=30000,
        ),
    )

    assert response.ok is False
    assert response.error is not None
    assert response.error.code == RuntimeErrorCode.TIMEOUT
