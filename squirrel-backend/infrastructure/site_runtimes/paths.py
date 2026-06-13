from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from infrastructure.config.settings import settings


@dataclass(frozen=True)
class SiteRuntimePaths:
    repo_root: Path
    workspace_runtimes_dir: Path
    state_dir: Path
    artifacts_dir: Path
    runtime_dir: Path
    runtime_data_dir: Path
    records_file: Path


def build_site_runtime_paths(repo_root: Path | None = None, backend_root: Path | None = None) -> SiteRuntimePaths:
    resolved_backend_root = (backend_root or settings.base_dir).resolve()
    resolved_repo_root = (repo_root or resolved_backend_root.parent).resolve()
    state_dir = resolved_repo_root / "data" / "site-runtimes" / "state"
    artifacts_dir = resolved_repo_root / "data" / "site-runtimes" / "artifacts"
    runtime_dir = resolved_repo_root / "data" / "site-runtimes" / "runtime"
    runtime_data_dir = resolved_repo_root / "data" / "site-runtimes" / "data"

    return SiteRuntimePaths(
        repo_root=resolved_repo_root,
        workspace_runtimes_dir=resolved_repo_root / "squirrel-site-runtimes",
        state_dir=state_dir,
        artifacts_dir=artifacts_dir,
        runtime_dir=runtime_dir,
        runtime_data_dir=runtime_data_dir,
        records_file=state_dir / "runtime_records.json",
    )


