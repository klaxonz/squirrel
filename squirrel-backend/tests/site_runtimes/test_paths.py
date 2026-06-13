import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.site_runtimes.paths import SiteRuntimePaths, build_site_runtime_paths


def test_build_site_runtime_paths_uses_data_directories(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True)

    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)

    assert isinstance(paths, SiteRuntimePaths)
    assert paths.state_dir == repo_root / "data" / "site-runtimes" / "state"
    assert paths.records_file == paths.state_dir / "runtime_records.json"
    assert paths.workspace_runtimes_dir == repo_root / "squirrel-site-runtimes"



