from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from crawl import PluginInvokeRequest
from site_runtimes.models import SiteRuntimeRecord, SiteRuntimeTarget, SiteRuntimeState
from site_runtimes.supervisor import SiteRuntimeSupervisor


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

    record = SiteRuntimeRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(plugin_root),
        runtime_path=str(plugin_root),
        entrypoint='sample_runtime:get_plugin_runtime',
        enabled=True,
        manifest={},
    )

    supervisor = SiteRuntimeSupervisor()
    handle = supervisor.start_runtime(record)

    assert handle.state == SiteRuntimeState.RUNNING
    assert handle.process_id
    assert handle.endpoint

    response = supervisor.invoke(
        SiteRuntimeTarget(
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
        SiteRuntimeTarget(
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
    assert stopped.state == SiteRuntimeState.STOPPED


def test_supervisor_builds_workspace_runtime_command(tmp_path):
    plugin_root = tmp_path / 'sample_plugin'
    plugin_root.mkdir()
    record = SiteRuntimeRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(plugin_root),
        runtime_path=str(plugin_root),
        data_path=str(tmp_path / 'data'),
        entrypoint='sample_runtime:get_plugin_runtime',
        enabled=True,
        manifest={
            'metadata': {
                'runtime_policy': {
                    'max_runtime_seconds': 3600,
                    'memory_limit_mb': 256,
                    'cpu_time_limit_seconds': 600,
                    'max_open_files': 128,
                },
                'network_policy': {
                    'mode': 'allow_list',
                    'allow_hosts': ['sample.test'],
                    'deny_hosts': ['blocked.test'],
                },
            }
        },
        granted_permissions=['network:http', 'cookies:read:site/sample'],
        metadata={'source': 'workspace'},
    )

    supervisor = SiteRuntimeSupervisor()

    command = supervisor._build_runtime_command(record, host='127.0.0.1', port=9001)

    assert command[1:3] == ['-m', 'site_runtimes.runtime_bridge']
    assert '--import-path' in command
    assert str(plugin_root) in command
    assert '--data-dir' in command
    assert str(tmp_path / 'data') in command
    assert '--granted-permission' in command
    assert '--network-policy' in command
    network_policy_index = command.index('--network-policy') + 1
    assert json.loads(command[network_policy_index]) == {
        'mode': 'allow_list',
        'allow_hosts': ['sample.test'],
        'deny_hosts': ['blocked.test'],
    }
    assert '--max-runtime-seconds' in command
    assert '--memory-limit-mb' in command
    assert '--cpu-time-limit-seconds' in command
    assert '--max-open-files' in command

    artifact_paths = supervisor._resolve_artifact_paths(record)
    assert artifact_paths['stdout'].name == 'stdout.log'
    assert artifact_paths['stderr'].name == 'stderr.log'
    assert artifact_paths['audit'].name == 'audit.jsonl'


def test_supervisor_sets_workspace_runtime_environment(monkeypatch, tmp_path):
    monkeypatch.setenv('PATH', r'C:\Windows\System32')
    record = SiteRuntimeRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(tmp_path / 'sample_plugin'),
        runtime_path=str(tmp_path / 'sample_plugin'),
        data_path=str(tmp_path / 'data'),
        entrypoint='sample_runtime:get_plugin_runtime',
        enabled=True,
        manifest={},
        granted_permissions=['network:http'],
        metadata={'source': 'workspace'},
    )

    supervisor = SiteRuntimeSupervisor()

    process_env = supervisor._build_process_env(record)

    assert process_env['SQUIRREL_PLUGIN_ID'] == 'sample'
    assert process_env['SQUIRREL_PLUGIN_VERSION'] == '0.1.0'
    assert process_env['SQUIRREL_PLUGIN_DATA_DIR'] == str(tmp_path / 'data')
    assert process_env['SQUIRREL_PLUGIN_GRANTED_PERMISSIONS'] == 'network:http'
    assert process_env['SQUIRREL_PLUGIN_SOURCE'] == 'workspace'


def test_supervisor_appends_audit_events(tmp_path):
    record = SiteRuntimeRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(tmp_path / 'sample_plugin'),
        runtime_path=str(tmp_path / 'sample_plugin'),
        data_path=str(tmp_path / 'data'),
        entrypoint='sample_runtime:get_plugin_runtime',
        enabled=True,
        manifest={},
    )
    supervisor = SiteRuntimeSupervisor()

    audit_path = supervisor._append_audit_event(
        record,
        event='runtime_started',
        details={'pid': 1234},
    )

    lines = audit_path.read_text(encoding='utf-8').strip().splitlines()
    assert len(lines) == 1
    payload = json.loads(lines[0])
    assert payload['plugin_id'] == 'sample'
    assert payload['version'] == '0.1.0'
    assert payload['event'] == 'runtime_started'
    assert payload['details'] == {'pid': 1234}


