import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.site_runtimes.models import SiteRuntimeRecord
from infrastructure.site_runtimes.paths import build_site_runtime_paths
from infrastructure.site_runtimes.store import SiteRuntimeStore


def test_store_list_records_tolerates_empty_json_file(tmp_path):
    data_path = tmp_path / "site_runtime_v2" / "runtime_records.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("", encoding="utf-8")

    store = SiteRuntimeStore(data_path=data_path)

    assert store.list_records() == []


def test_store_upsert_repairs_empty_json_file(tmp_path):
    data_path = tmp_path / "site_runtime_v2" / "runtime_records.json"
    data_path.parent.mkdir(parents=True, exist_ok=True)
    data_path.write_text("", encoding="utf-8")

    store = SiteRuntimeStore(data_path=data_path)
    record = SiteRuntimeRecord(
        runtime_id="sample",
        version="0.1.0",
        install_path=str(tmp_path / "sample"),
        entrypoint="sample.runtime:get_site_runtime",
        enabled=True,
        manifest={"runtime_id": "sample", "version": "0.1.0", "capabilities": [], "sites": []},
    )

    store.upsert(record)

    repaired = store.get_record("sample")
    assert repaired is not None
    assert repaired.runtime_id == "sample"


def test_store_cleans_stale_temp_files_on_init(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    stale = paths.state_dir / "runtime_records.orphan.tmp"
    stale.write_text("orphan", encoding="utf-8")

    store = SiteRuntimeStore(paths=paths)

    assert store.data_path == paths.records_file
    assert not stale.exists()


def test_store_write_failure_removes_new_temp_file(monkeypatch, tmp_path):
    data_path = tmp_path / "site-runtimes" / "runtime_records.json"
    store = SiteRuntimeStore(data_path=data_path)
    record = SiteRuntimeRecord(
        runtime_id="sample",
        version="0.1.0",
        install_path=str(tmp_path / "sample"),
        entrypoint="sample.runtime:get_site_runtime",
        enabled=True,
        manifest={"runtime_id": "sample", "version": "0.1.0", "capabilities": [], "sites": []},
    )

    monkeypatch.setattr("site_runtimes.store.os.replace", lambda *_args, **_kwargs: (_ for _ in ()).throw(PermissionError("locked")))

    with pytest.raises(PermissionError, match="locked"):
        store.upsert(record)

    assert not list(data_path.parent.glob("runtime_records.*.tmp"))



