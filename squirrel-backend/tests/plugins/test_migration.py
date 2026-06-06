import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.migration import migrate_legacy_plugin_storage
from plugins.paths import build_plugin_paths


def test_migrate_legacy_plugin_storage_moves_runtime_layout(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)

    legacy = paths.legacy_root
    (legacy / 'runtime').mkdir(parents=True)
    (legacy / 'data').mkdir(parents=True)
    (legacy / 'runtime' / 'demo').mkdir(parents=True)
    (legacy / 'runtime' / 'demo' / 'python.txt').write_text('runtime', encoding='utf-8')
    (legacy / 'data' / 'demo').mkdir(parents=True)
    (legacy / 'data' / 'demo' / 'state.txt').write_text('data', encoding='utf-8')
    (legacy / 'installations.json').write_text(
        json.dumps({'demo': {'plugin_id': 'demo'}}, ensure_ascii=False),
        encoding='utf-8',
    )
    (legacy / 'installations.stale.tmp').write_text('stale', encoding='utf-8')

    migrated = migrate_legacy_plugin_storage(paths)

    assert migrated is True
    assert paths.installations_file.exists()
    assert (paths.runtime_dir / 'demo' / 'python.txt').exists()
    assert (paths.plugin_data_dir / 'demo' / 'state.txt').exists()
    assert not (legacy / 'installations.stale.tmp').exists()


def test_migrate_legacy_plugin_storage_skips_when_new_state_exists(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)

    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.installations_file.write_text('{}', encoding='utf-8')
    paths.legacy_root.mkdir(parents=True, exist_ok=True)

    migrated = migrate_legacy_plugin_storage(paths)

    assert migrated is False
