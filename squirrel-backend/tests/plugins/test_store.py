from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.paths import build_plugin_paths
from plugins.models import PluginInstallRecord
from plugins.store import PluginInstallStore


def test_store_list_records_tolerates_empty_json_file(tmp_path):
    data_path = tmp_path / 'plugin_runtime_v2' / 'installations.json'
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text('', encoding='utf-8')

    store = PluginInstallStore(data_path=data_path)

    assert store.list_records() == []


def test_store_upsert_repairs_empty_json_file(tmp_path):
    data_path = tmp_path / 'plugin_runtime_v2' / 'installations.json'
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text('', encoding='utf-8')

    store = PluginInstallStore(data_path=data_path)
    record = PluginInstallRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(tmp_path / 'sample'),
        entrypoint='sample.runtime:get_plugin_runtime',
        enabled=True,
        manifest={'plugin_id': 'sample', 'version': '0.1.0', 'capabilities': [], 'sites': []},
    )

    store.upsert(record)

    repaired = store.get_record('sample')
    assert repaired is not None
    assert repaired.plugin_id == 'sample'


def test_store_cleans_stale_temp_files_on_init(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    stale = paths.state_dir / 'installations.orphan.tmp'
    stale.write_text('orphan', encoding='utf-8')

    store = PluginInstallStore(paths=paths)

    assert store.data_path == paths.installations_file
    assert not stale.exists()


def test_store_write_failure_removes_new_temp_file(monkeypatch, tmp_path):
    data_path = tmp_path / 'plugin-runtime' / 'installations.json'
    store = PluginInstallStore(data_path=data_path)
    record = PluginInstallRecord(
        plugin_id='sample',
        version='0.1.0',
        install_path=str(tmp_path / 'sample'),
        entrypoint='sample.runtime:get_plugin_runtime',
        enabled=True,
        manifest={'plugin_id': 'sample', 'version': '0.1.0', 'capabilities': [], 'sites': []},
    )

    monkeypatch.setattr('plugins.store.os.replace', lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError('locked')))

    with pytest.raises(PermissionError, match='locked'):
        store.upsert(record)

    assert not list(data_path.parent.glob('installations.*.tmp'))
