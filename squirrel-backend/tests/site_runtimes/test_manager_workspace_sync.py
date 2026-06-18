import json
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from infrastructure.site_runtimes.manager import SiteRuntimeManager
from infrastructure.site_runtimes.models import (
    SiteRuntimeCapability,
    SiteRuntimeManifest,
    SiteRuntimeRecord,
    SiteRuntimeSite,
    SiteRuntimeStatus,
)
from infrastructure.site_runtimes.paths import build_site_runtime_paths
from infrastructure.site_runtimes.store import SiteRuntimeStore


def _write_runtime_metadata(repo_root: Path, runtime_id: str, domain: str) -> SiteRuntimeManifest:
    runtime_root = repo_root / "squirrel-site-runtimes" / runtime_id
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "src").mkdir(parents=True, exist_ok=True)
    manifest = SiteRuntimeManifest(
        runtime_id=runtime_id,
        version="0.1.0",
        capabilities=[
            SiteRuntimeCapability(name="resolve_subscription", timeout_ms=30000),
        ],
        sites=[
            SiteRuntimeSite(site_name=runtime_id, domains=[domain]),
        ],
    )
    (runtime_root / "site-runtime.json").write_text(
        json.dumps(
            {
                "entrypoint": f"squirrel_{runtime_id}.runtime:get_site_runtime",
                "manifest": manifest.to_dict(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return manifest


def _create_enabled_record(repo_root: Path, runtime_id: str, domain: str) -> SiteRuntimeRecord:
    manifest = _write_runtime_metadata(repo_root, runtime_id, domain)
    runtime_root = repo_root / "squirrel-site-runtimes" / runtime_id
    return SiteRuntimeRecord(
        runtime_id=runtime_id,
        version="0.1.0",
        install_path=str(runtime_root),
        entrypoint=f"squirrel_{runtime_id}.runtime:get_site_runtime",
        enabled=True,
        status=SiteRuntimeStatus.INSTALLED,
        manifest=manifest.to_dict(),
        runtime_path=str(runtime_root / "src"),
        metadata={"source": "workspace"},
    )


def test_discover_site_runtimes_refreshes_existing_workspace_manifest(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    runtimes_root = repo_root / "squirrel-site-runtimes" / "javdb"
    runtimes_root.mkdir(parents=True, exist_ok=True)
    (runtimes_root / "src").mkdir(parents=True, exist_ok=True)
    metadata_path = runtimes_root / "site-runtime.json"
    metadata_path.write_text(
        json.dumps(
            {
                "entrypoint": "squirrel_javdb.runtime:get_site_runtime",
                "manifest": {
                    "runtime_id": "javdb",
                    "version": "0.1.0",
                    "display_name": "JavDB",
                    "description": "JavDB crawl integration",
                    "capabilities": [
                        {
                            "name": "check_login_status",
                            "response_schema": {"type": "object"},
                            "timeout_ms": 30000,
                        },
                        {
                            "name": "extract_video",
                            "response_schema": {"type": "object"},
                            "timeout_ms": 30000,
                        },
                    ],
                    "sites": [
                        {
                            "site_name": "javdb",
                            "domains": ["javdb.com"],
                            "features": ["check_login_status", "extract_video"],
                        },
                    ],
                    "permissions": [
                        {"name": "network:http"},
                        {"name": "cookies:read:site/javdb"},
                    ],
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    store = SiteRuntimeStore(data_path=paths.records_file, paths=paths)
    store.upsert(
        SiteRuntimeRecord(
            runtime_id="javdb",
            version="0.1.0",
            install_path=str(runtimes_root),
            entrypoint="old.entrypoint:get_site_runtime",
            enabled=True,
            manifest={
                "runtime_id": "javdb",
                "version": "0.1.0",
                "capabilities": [
                    {
                        "name": "check_login_status",
                        "response_schema": {"type": "object"},
                        "timeout_ms": 15000,
                    },
                ],
                "sites": [
                    {
                        "site_name": "javdb",
                        "domains": ["javdb.com"],
                        "features": ["check_login_status"],
                    },
                ],
                "permissions": [
                    {"name": "network:http"},
                ],
            },
            runtime_path=str(runtimes_root),
            metadata={"source": "workspace"},
        ),
    )

    manager = SiteRuntimeManager(
        store=store,
        paths=paths,
    )

    manager.sync_workspace()

    record = store.get_record("javdb")
    assert record is not None
    assert record.entrypoint == "squirrel_javdb.runtime:get_site_runtime"
    assert record.runtime_path == str(runtimes_root / "src")
    assert [item["name"] for item in record.manifest["capabilities"]] == ["check_login_status", "extract_video"]
    assert record.manifest["capabilities"][0]["timeout_ms"] == 30000
    assert record.granted_permissions == ["network:http", "cookies:read:site/javdb"]

    upserted_runtime_ids = []
    original_upsert = store.upsert

    def track_upsert(record):
        upserted_runtime_ids.append(record.runtime_id)
        return original_upsert(record)

    monkeypatch.setattr(store, "upsert", track_upsert)

    # Second call must be idempotent: scan is pure read, no further writes.
    manager.sync_workspace()

    assert upserted_runtime_ids == []


def test_sync_workspace_does_not_register_unstarted_runtimes(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    store = SiteRuntimeStore(data_path=paths.records_file, paths=paths)

    runtime_root = repo_root / "squirrel-site-runtimes" / "youporn"
    runtime_root.mkdir(parents=True, exist_ok=True)
    (runtime_root / "src").mkdir(parents=True, exist_ok=True)
    manifest = SiteRuntimeManifest(
        runtime_id="youporn",
        version="0.1.0",
        capabilities=[
            SiteRuntimeCapability(name="resolve_subscription", timeout_ms=30000),
        ],
        sites=[
            SiteRuntimeSite(site_name="youporn", domains=["youporn.com"]),
        ],
    )
    (runtime_root / "site-runtime.json").write_text(
        json.dumps(
            {
                "entrypoint": "squirrel_youporn.runtime:get_site_runtime",
                "manifest": manifest.to_dict(),
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    # Pre-seed store with a stale record so sync detects a change.
    store.upsert(
        SiteRuntimeRecord(
            runtime_id="youporn",
            version="0.1.0",
            install_path=str(runtime_root),
            entrypoint="old.entrypoint:get_site_runtime",
            enabled=True,
            manifest=manifest.to_dict(),
            runtime_path=str(runtime_root / "src"),
            metadata={"source": "workspace"},
        ),
    )

    manager = SiteRuntimeManager(
        store=store,
        paths=paths,
    )

    assert manager.gateway.resolve_route("resolve_subscription", domain="youporn.com") is None
    manager.sync_workspace()

    assert manager.gateway.resolve_route("resolve_subscription", domain="youporn.com") is None


def test_manager_ignores_non_workspace_records(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    store = SiteRuntimeStore(data_path=paths.records_file, paths=paths)
    store.upsert(
        SiteRuntimeRecord(
            runtime_id="uploaded",
            version="0.1.0",
            install_path=str(tmp_path / "uploaded"),
            entrypoint="uploaded.runtime:get_site_runtime",
            enabled=True,
            manifest=SiteRuntimeManifest(
                runtime_id="uploaded",
                version="0.1.0",
                capabilities=[SiteRuntimeCapability(name="extract_video")],
                sites=[SiteRuntimeSite(site_name="uploaded", domains=["uploaded.test"])],
            ).to_dict(),
            metadata={"source": "upload"},
        ),
    )

    manager = SiteRuntimeManager(store=store, paths=paths)

    assert manager.list_site_runtimes() == []
    assert manager.get_site_runtime("uploaded") is None
    assert manager.enable_site_runtime("uploaded") is None
    assert manager.gateway.resolve_route("extract_video", domain="uploaded.test") is None


def test_manager_uses_shared_paths_for_workspace_discovery(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)

    manager = SiteRuntimeManager(paths=paths)

    assert manager._paths.workspace_runtimes_dir == repo_root / "squirrel-site-runtimes"


def test_sync_workspace_removes_deleted_workspace_runtime(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    store = SiteRuntimeStore(data_path=paths.records_file, paths=paths)
    store.upsert(_create_enabled_record(repo_root, "oldsite", "oldsite.test"))
    (repo_root / "squirrel-site-runtimes" / "oldsite" / "site-runtime.json").unlink()

    manager = SiteRuntimeManager(store=store, paths=paths)

    result = manager.sync_workspace()

    assert result.records == []
    assert store.get_record("oldsite") is None


def test_bootstrap_enabled_site_runtimes_starts_runtimes_in_parallel_and_preserves_order(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    store = SiteRuntimeStore(data_path=paths.records_file, paths=paths)
    for runtime_id in ("alpha", "beta", "gamma"):
        store.upsert(_create_enabled_record(repo_root, runtime_id, f"{runtime_id}.test"))

    class _ParallelSupervisor:
        def __init__(self) -> None:
            self.barrier = threading.Barrier(3, timeout=3)
            self.started: list[str] = []
            self._lock = threading.Lock()

        def start_runtime(self, record: SiteRuntimeRecord):
            self.barrier.wait()
            with self._lock:
                self.started.append(record.runtime_id)
            return object()

    supervisor = _ParallelSupervisor()
    manager = SiteRuntimeManager(
        store=store,
        supervisor=supervisor,
        paths=paths,
    )

    started = manager.bootstrap_enabled_site_runtimes()

    assert sorted(supervisor.started) == ["alpha", "beta", "gamma"]
    assert [record.runtime_id for record in started] == ["alpha", "beta", "gamma"]
    assert store.get_record("alpha").status == SiteRuntimeStatus.RUNNING
    assert store.get_record("beta").status == SiteRuntimeStatus.RUNNING
    assert store.get_record("gamma").status == SiteRuntimeStatus.RUNNING
    assert manager.gateway.resolve_route("resolve_subscription", domain="gamma.test").runtime_id == "gamma"


def test_bootstrap_enabled_site_runtimes_raises_after_persisting_successful_starts(tmp_path):
    repo_root = tmp_path / "repo"
    backend_root = repo_root / "squirrel-backend"
    backend_root.mkdir(parents=True, exist_ok=True)
    paths = build_site_runtime_paths(repo_root=repo_root, backend_root=backend_root)
    store = SiteRuntimeStore(data_path=paths.records_file, paths=paths)
    for runtime_id in ("alpha", "beta", "gamma"):
        store.upsert(_create_enabled_record(repo_root, runtime_id, f"{runtime_id}.test"))

    class _FailingSupervisor:
        def __init__(self) -> None:
            self.started: list[str] = []

        def start_runtime(self, record: SiteRuntimeRecord):
            if record.runtime_id == "beta":
                raise RuntimeError("boom beta")
            self.started.append(record.runtime_id)
            return object()

    supervisor = _FailingSupervisor()
    manager = SiteRuntimeManager(
        store=store,
        supervisor=supervisor,
        paths=paths,
    )

    with pytest.raises(RuntimeError, match="boom beta"):
        manager.bootstrap_enabled_site_runtimes()

    assert sorted(supervisor.started) == ["alpha", "gamma"]
    assert store.get_record("alpha").status == SiteRuntimeStatus.RUNNING
    # Failed runtimes are persisted as FAILED so the store reflects reality.
    assert store.get_record("beta").status == SiteRuntimeStatus.FAILED
    assert store.get_record("gamma").status == SiteRuntimeStatus.RUNNING
    assert manager.gateway.resolve_route("resolve_subscription", domain="beta.test") is None
    assert manager.gateway.resolve_route("resolve_subscription", domain="alpha.test").runtime_id == "alpha"


