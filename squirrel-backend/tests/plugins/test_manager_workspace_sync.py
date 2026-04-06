from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.installer import PluginInstaller
from plugins.manager import PluginManager
from plugins.models import PluginInstallRecord
from plugins.paths import build_plugin_paths
from plugins.store import PluginInstallStore
from plugins.runtime_models import PluginCapability, PluginManifest, PluginSiteManifest


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
