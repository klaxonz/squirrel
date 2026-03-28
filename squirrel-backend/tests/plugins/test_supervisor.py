from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeRequest
from plugins.models import PluginInstallRecord, PluginRoutingTarget, PluginRuntimeState
from plugins.supervisor import PluginRuntimeSupervisor


def test_supervisor_runs_plugin_runtime_in_subprocess(tmp_path):
    plugin_root = tmp_path / 'sample_plugin'
    plugin_root.mkdir()
    module_path = plugin_root / 'sample_runtime.py'
    module_path.write_text(
        """
from datetime import datetime

from crawl import PluginHealthStatus, PluginManifest, create_plugin_runtime


def get_plugin_runtime():
    return create_plugin_runtime(
        manifest=PluginManifest(
            plugin_id='sample',
            version='0.1.0',
            capabilities=[],
            sites=[],
        ),
        capability_handlers={
            'echo': lambda payload: {'echo': payload.get('value')},
            'echo_datetime': lambda payload: {'created_at': datetime(2024, 1, 1, 12, 0, 0)},
        },
        health_check=lambda: PluginHealthStatus(healthy=True, status='ready', message='ok'),
    )
""".strip(),
        encoding='utf-8',
    )

    record = PluginInstallRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(plugin_root),
        runtime_path=str(plugin_root),
        entrypoint='sample_runtime:get_plugin_runtime',
        enabled=True,
        manifest={},
    )

    supervisor = PluginRuntimeSupervisor()
    handle = supervisor.start_runtime(record)

    assert handle.state == PluginRuntimeState.RUNNING
    assert handle.process_id
    assert handle.endpoint

    response = supervisor.invoke(
        PluginRoutingTarget(
            plugin_id='sample',
            version='0.1.0',
            capability='echo',
            site_name='sample',
        ),
        PluginInvokeRequest(
            request_id='req-1',
            capability='echo',
            payload={'value': 'hello'},
            site_name='sample',
        ),
    )

    assert response.ok is True
    assert response.data == {'echo': 'hello'}

    datetime_response = supervisor.invoke(
        PluginRoutingTarget(
            plugin_id='sample',
            version='0.1.0',
            capability='echo_datetime',
            site_name='sample',
        ),
        PluginInvokeRequest(
            request_id='req-2',
            capability='echo_datetime',
            payload={},
            site_name='sample',
        ),
    )

    assert datetime_response.ok is True
    assert datetime_response.data == {'created_at': '2024-01-01T12:00:00'}

    stopped = supervisor.stop_runtime('sample', '0.1.0')

    assert stopped is not None
    assert stopped.state == PluginRuntimeState.STOPPED
