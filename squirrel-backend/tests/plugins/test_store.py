from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

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
