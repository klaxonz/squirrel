from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from plugins.paths import PluginPaths, build_plugin_paths


def test_build_plugin_paths_uses_data_directories(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)

    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)

    assert isinstance(paths, PluginPaths)
    assert paths.state_dir == repo_root / 'data' / 'plugins' / 'state'
    assert paths.installations_file == paths.state_dir / 'installations.json'
    assert paths.workspace_plugins_dir == repo_root / 'squirrel-plugins'
    assert paths.legacy_root == repo_root / 'config' / 'plugin_runtime_v2'

