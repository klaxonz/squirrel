from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from core.config import settings


@dataclass(frozen=True)
class PluginPaths:
    repo_root: Path
    workspace_plugins_dir: Path
    state_dir: Path
    artifacts_dir: Path
    runtime_dir: Path
    plugin_data_dir: Path
    installations_file: Path
    legacy_root: Path


def build_plugin_paths(repo_root: Path | None = None, backend_root: Path | None = None) -> PluginPaths:
    resolved_backend_root = (backend_root or settings.base_dir).resolve()
    resolved_repo_root = (repo_root or resolved_backend_root.parent).resolve()
    state_dir = resolved_repo_root / 'data' / 'plugins' / 'state'
    artifacts_dir = resolved_repo_root / 'data' / 'plugins' / 'artifacts'
    runtime_dir = resolved_repo_root / 'data' / 'plugins' / 'runtime'
    plugin_data_dir = resolved_repo_root / 'data' / 'plugins' / 'data'

    return PluginPaths(
        repo_root=resolved_repo_root,
        workspace_plugins_dir=resolved_repo_root / 'squirrel-plugins',
        state_dir=state_dir,
        artifacts_dir=artifacts_dir,
        runtime_dir=runtime_dir,
        plugin_data_dir=plugin_data_dir,
        installations_file=state_dir / 'installations.json',
        legacy_root=resolved_repo_root / 'config' / 'plugin_runtime_v2',
    )
