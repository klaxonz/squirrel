from pathlib import Path
import json
import sys
import threading

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.installer import PluginInstaller
from plugins.manager import PluginManager
from plugins.models import PluginInstallRecord, PluginInstallStatus
from plugins.paths import build_plugin_paths
from plugins.store import PluginInstallStore
from plugins.runtime_models import PluginCapability, PluginManifest, PluginSiteManifest


def _create_enabled_record(repo_root: Path, plugin_id: str, domain: str) -> PluginInstallRecord:
    plugin_root = repo_root / 'squirrel-plugins' / plugin_id
    return PluginInstallRecord(
        plugin_id=plugin_id,
        version='0.1.0',
        install_path=str(plugin_root),
        entrypoint=f'squirrel_{plugin_id}.runtime:get_plugin_runtime',
        enabled=True,
        status=PluginInstallStatus.INSTALLED,
        manifest=PluginManifest(
            plugin_id=plugin_id,
            version='0.1.0',
            capabilities=[
                PluginCapability(name='resolve_subscription', timeout_ms=30000),
            ],
            sites=[
                PluginSiteManifest(site_name=plugin_id, domains=[domain]),
            ],
        ).to_dict(),
        runtime_path=str(plugin_root / 'src'),
        metadata={'source': 'workspace'},
    )


def test_discover_plugins_refreshes_existing_workspace_manifest(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)
    plugins_root = repo_root / 'squirrel-plugins' / 'javdb'
    plugins_root.mkdir(parents=True, exist_ok=True)
    (plugins_root / 'src').mkdir(parents=True, exist_ok=True)
    metadata_path = plugins_root / 'plugin-runtime.json'
    metadata_path.write_text(
        json.dumps(
            {
                'entrypoint': 'squirrel_javdb.runtime:get_plugin_runtime',
                'manifest': {
                    'plugin_id': 'javdb',
                    'version': '0.1.0',
                    'display_name': 'JavDB',
                    'description': 'JavDB crawl integration',
                    'capabilities': [
                        {
                            'name': 'check_login_status',
                            'response_schema': {'type': 'object'},
                            'timeout_ms': 30000,
                        },
                        {
                            'name': 'resolve_playback',
                            'response_schema': {'type': 'object'},
                            'timeout_ms': 30000,
                        },
                    ],
                    'sites': [
                        {
                            'site_name': 'javdb',
                            'domains': ['javdb.com'],
                            'features': ['check_login_status', 'resolve_playback'],
                        },
                    ],
                    'permissions': [
                        {'name': 'network:http'},
                        {'name': 'cookies:read:site/javdb'},
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding='utf-8',
    )

    store = PluginInstallStore(data_path=paths.installations_file, paths=paths)
    store.upsert(
        PluginInstallRecord(
            plugin_id='javdb',
            version='0.1.0',
            install_path=str(plugins_root),
            entrypoint='old.entrypoint:get_plugin_runtime',
            enabled=True,
            manifest={
                'plugin_id': 'javdb',
                'version': '0.1.0',
                'capabilities': [
                    {
                        'name': 'check_login_status',
                        'response_schema': {'type': 'object'},
                        'timeout_ms': 15000,
                    },
                ],
                'sites': [
                    {
                        'site_name': 'javdb',
                        'domains': ['javdb.com'],
                        'features': ['check_login_status'],
                    },
                ],
                'permissions': [
                    {'name': 'network:http'},
                ],
            },
            runtime_path=str(plugins_root),
            metadata={'source': 'workspace'},
        ),
    )

    manager = PluginManager(
        store=store,
        installer=PluginInstaller(paths=paths),
        paths=paths,
    )

    manager.discover_plugins()

    record = store.get_record('javdb')
    assert record is not None
    assert record.entrypoint == 'squirrel_javdb.runtime:get_plugin_runtime'
    assert record.runtime_path == str(plugins_root / 'src')
    assert [item['name'] for item in record.manifest['capabilities']] == ['check_login_status', 'resolve_playback']
    assert record.manifest['capabilities'][0]['timeout_ms'] == 30000
    assert record.granted_permissions == ['network:http', 'cookies:read:site/javdb']


def test_manager_gateway_rebuilds_enabled_registrations_on_route_miss(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)
    store = PluginInstallStore(data_path=paths.installations_file, paths=paths)
    store.upsert(
        PluginInstallRecord(
            plugin_id='youporn',
            version='0.1.0',
            install_path=str(repo_root / 'squirrel-plugins' / 'youporn'),
            entrypoint='squirrel_youporn.runtime:get_plugin_runtime',
            enabled=True,
            manifest=PluginManifest(
                plugin_id='youporn',
                version='0.1.0',
                capabilities=[
                    PluginCapability(name='resolve_subscription', timeout_ms=30000),
                ],
                sites=[
                    PluginSiteManifest(site_name='youporn', domains=['youporn.com']),
                ],
            ).to_dict(),
            runtime_path=str(repo_root / 'squirrel-plugins' / 'youporn' / 'src'),
            metadata={'source': 'workspace'},
        ),
    )

    manager = PluginManager(
        store=store,
        installer=PluginInstaller(paths=paths),
        paths=paths,
    )

    route = manager.gateway.resolve_route('resolve_subscription', domain='youporn.com')

    assert route is not None
    assert route.plugin_id == 'youporn'


def test_manager_uses_shared_paths_for_workspace_discovery(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)

    manager = PluginManager(paths=paths)

    assert manager._paths.workspace_plugins_dir == repo_root / 'squirrel-plugins'


def test_bootstrap_enabled_plugins_starts_runtimes_in_parallel_and_preserves_order(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)
    store = PluginInstallStore(data_path=paths.installations_file, paths=paths)
    for plugin_id in ('alpha', 'beta', 'gamma'):
        store.upsert(_create_enabled_record(repo_root, plugin_id, f'{plugin_id}.test'))

    class _ParallelSupervisor:
        def __init__(self) -> None:
            self.barrier = threading.Barrier(3, timeout=3)
            self.started: list[str] = []
            self._lock = threading.Lock()

        def start_runtime(self, record: PluginInstallRecord):
            self.barrier.wait()
            with self._lock:
                self.started.append(record.plugin_id)
            return object()

    supervisor = _ParallelSupervisor()
    manager = PluginManager(
        store=store,
        installer=PluginInstaller(paths=paths),
        supervisor=supervisor,
        paths=paths,
    )

    started = manager.bootstrap_enabled_plugins()

    assert sorted(supervisor.started) == ['alpha', 'beta', 'gamma']
    assert [record.plugin_id for record in started] == ['alpha', 'beta', 'gamma']
    assert store.get_record('alpha').status == PluginInstallStatus.RUNNING
    assert store.get_record('beta').status == PluginInstallStatus.RUNNING
    assert store.get_record('gamma').status == PluginInstallStatus.RUNNING
    assert manager.gateway.resolve_route('resolve_subscription', domain='gamma.test').plugin_id == 'gamma'


def test_bootstrap_enabled_plugins_raises_after_persisting_successful_starts(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)
    store = PluginInstallStore(data_path=paths.installations_file, paths=paths)
    for plugin_id in ('alpha', 'beta', 'gamma'):
        store.upsert(_create_enabled_record(repo_root, plugin_id, f'{plugin_id}.test'))

    class _FailingSupervisor:
        def __init__(self) -> None:
            self.started: list[str] = []

        def start_runtime(self, record: PluginInstallRecord):
            if record.plugin_id == 'beta':
                raise RuntimeError('boom beta')
            self.started.append(record.plugin_id)
            return object()

    supervisor = _FailingSupervisor()
    manager = PluginManager(
        store=store,
        installer=PluginInstaller(paths=paths),
        supervisor=supervisor,
        paths=paths,
    )

    with pytest.raises(RuntimeError, match='boom beta'):
        manager.bootstrap_enabled_plugins()

    assert sorted(supervisor.started) == ['alpha', 'gamma']
    assert store.get_record('alpha').status == PluginInstallStatus.RUNNING
    assert store.get_record('beta').status == PluginInstallStatus.INSTALLED
    assert store.get_record('gamma').status == PluginInstallStatus.RUNNING
