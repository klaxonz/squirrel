# Plugin Runtime Storage Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move plugin runtime storage out of `config/`, centralize path layout in one shared contract, add one-time migration from the legacy layout, and eliminate stale temp-file buildup in the plugin installation store.

**Architecture:** Introduce a new `plugins.paths` module as the storage contract, a `plugins.migration` module for one-time legacy migration, then refactor `store`, `installer`, and `manager` to depend on shared paths instead of implicit path construction. Preserve the current JSON-backed store and workspace plugin discovery behavior while changing only local storage layout and cleanup behavior.

**Tech Stack:** Python 3, FastAPI backend support modules, pathlib, JSON persistence, pytest

---

### Task 1: Introduce shared plugin storage paths

**Files:**
- Create: `squirrel-backend/plugins/paths.py`
- Modify: `squirrel-backend/plugins/__init__.py`
- Test: `squirrel-backend/tests/plugins/test_paths.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from plugins.paths import PluginPaths, build_plugin_paths


def test_build_plugin_paths_uses_data_directories(tmp_path: Path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)

    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)

    assert isinstance(paths, PluginPaths)
    assert paths.state_dir == repo_root / 'data' / 'plugins' / 'state'
    assert paths.installations_file == paths.state_dir / 'installations.json'
    assert paths.workspace_plugins_dir == repo_root / 'squirrel-plugins'
    assert paths.legacy_root == repo_root / 'config' / 'plugin_runtime_v2'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_paths.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing symbol errors for `plugins.paths`

- [ ] **Step 3: Write minimal implementation**

```python
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
    packages_dir: Path
    installs_dir: Path
    runtime_dir: Path
    plugin_data_dir: Path
    installations_file: Path
    legacy_root: Path


def build_plugin_paths(repo_root: Path | None = None, backend_root: Path | None = None) -> PluginPaths:
    resolved_backend_root = (backend_root or settings.base_dir).resolve()
    resolved_repo_root = (repo_root or resolved_backend_root.parent).resolve()
    state_dir = resolved_repo_root / 'data' / 'plugins' / 'state'
    artifacts_dir = resolved_repo_root / 'data' / 'plugins' / 'artifacts'
    return PluginPaths(
        repo_root=resolved_repo_root,
        workspace_plugins_dir=resolved_repo_root / 'squirrel-plugins',
        state_dir=state_dir,
        artifacts_dir=artifacts_dir,
        packages_dir=artifacts_dir / 'packages',
        installs_dir=artifacts_dir / 'installs',
        runtime_dir=resolved_repo_root / 'data' / 'plugins' / 'runtime',
        plugin_data_dir=resolved_repo_root / 'data' / 'plugins' / 'data',
        installations_file=state_dir / 'installations.json',
        legacy_root=resolved_repo_root / 'config' / 'plugin_runtime_v2',
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_paths.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/plugins/paths.py squirrel-backend/plugins/__init__.py squirrel-backend/tests/plugins/test_paths.py
git commit -m "refactor: add shared plugin storage paths"
```

### Task 2: Add one-time legacy storage migration

**Files:**
- Create: `squirrel-backend/plugins/migration.py`
- Test: `squirrel-backend/tests/plugins/test_migration.py`

- [ ] **Step 1: Write the failing test**

```python
import json
from pathlib import Path

from plugins.migration import migrate_legacy_plugin_storage
from plugins.paths import build_plugin_paths


def test_migrate_legacy_plugin_storage_moves_runtime_layout(tmp_path: Path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)

    legacy = paths.legacy_root
    (legacy / 'packages').mkdir(parents=True)
    (legacy / 'installs').mkdir(parents=True)
    (legacy / 'runtime').mkdir(parents=True)
    (legacy / 'data').mkdir(parents=True)
    (legacy / 'installations.json').write_text(json.dumps({'demo': {'plugin_id': 'demo'}}), encoding='utf-8')
    (legacy / 'installations.stale.tmp').write_text('stale', encoding='utf-8')

    migrated = migrate_legacy_plugin_storage(paths)

    assert migrated is True
    assert paths.installations_file.exists()
    assert not (legacy / 'installations.stale.tmp').exists()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_migration.py -v`
Expected: FAIL with `ModuleNotFoundError` or missing symbol errors for `plugins.migration`

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import shutil

from .paths import PluginPaths


def migrate_legacy_plugin_storage(paths: PluginPaths) -> bool:
    if paths.installations_file.exists():
        return False
    if not paths.legacy_root.exists():
        return False

    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    paths.plugin_data_dir.mkdir(parents=True, exist_ok=True)

    legacy_installations = paths.legacy_root / 'installations.json'
    if legacy_installations.exists():
        shutil.move(str(legacy_installations), str(paths.installations_file))

    for name, target in {
        'packages': paths.packages_dir,
        'installs': paths.installs_dir,
        'runtime': paths.runtime_dir,
        'data': paths.plugin_data_dir,
    }.items():
        source = paths.legacy_root / name
        if source.exists() and not target.exists():
            shutil.move(str(source), str(target))

    for stale in paths.legacy_root.glob('installations.*.tmp'):
        stale.unlink(missing_ok=True)

    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_migration.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/plugins/migration.py squirrel-backend/tests/plugins/test_migration.py
git commit -m "refactor: migrate legacy plugin runtime storage"
```

### Task 3: Refactor store to use shared paths and cleanup temp files

**Files:**
- Modify: `squirrel-backend/plugins/store.py`
- Modify: `squirrel-backend/tests/plugins/test_store.py`

- [ ] **Step 1: Write the failing test**

```python
from pathlib import Path

from plugins.paths import build_plugin_paths
from plugins.store import PluginInstallStore


def test_store_cleans_stale_temp_files_on_init(tmp_path: Path):
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_store.py -v`
Expected: FAIL because `PluginInstallStore` does not accept `paths` and stale temp cleanup is missing

- [ ] **Step 3: Write minimal implementation**

```python
class PluginInstallStore:
    def __init__(self, data_path: Optional[Path] = None, paths: PluginPaths | None = None) -> None:
        self._paths = paths or build_plugin_paths()
        self._data_path = data_path or self._paths.installations_file
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_temp_files()

    def _cleanup_stale_temp_files(self) -> None:
        pattern = f'{self._data_path.stem}.*.tmp'
        for candidate in self._data_path.parent.glob(pattern):
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                logger.warning('Failed to remove stale plugin store temp file: %s', candidate)

    def _save_raw(self, records: Dict[str, Dict]) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(...snip...) as handle:
                ...
                temp_path = Path(handle.name)
            os.replace(temp_path, self._data_path)
        except Exception:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink(missing_ok=True)
            raise
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_store.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/plugins/store.py squirrel-backend/tests/plugins/test_store.py
git commit -m "fix: clean plugin store temp files and use shared paths"
```

### Task 4: Refactor installer and manager to consume shared paths

**Files:**
- Modify: `squirrel-backend/plugins/installer.py`
- Modify: `squirrel-backend/plugins/manager.py`
- Modify: `squirrel-backend/tests/plugins/test_manager_workspace_sync.py`
- Modify: `squirrel-backend/tests/plugins/test_installer.py`

- [ ] **Step 1: Write the failing test**

```python
from plugins.installer import PluginInstaller
from plugins.manager import PluginManager
from plugins.paths import build_plugin_paths


def test_manager_discovers_workspace_plugins_without_installer_private_base_dir(tmp_path):
    repo_root = tmp_path / 'repo'
    backend_root = repo_root / 'squirrel-backend'
    backend_root.mkdir(parents=True)
    paths = build_plugin_paths(repo_root=repo_root, backend_root=backend_root)
    manager = PluginManager(paths=paths)

    assert manager._paths.workspace_plugins_dir == repo_root / 'squirrel-plugins'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_manager_workspace_sync.py tests/plugins/test_installer.py -v`
Expected: FAIL because `PluginManager` and `PluginInstaller` do not accept shared `paths`

- [ ] **Step 3: Write minimal implementation**

```python
class PluginInstaller:
    def __init__(self, base_dir: Optional[Path] = None, paths: PluginPaths | None = None) -> None:
        self._paths = paths or build_plugin_paths()
        self._packages_dir = base_dir / 'packages' if base_dir else self._paths.packages_dir
        self._install_root = base_dir / 'installs' if base_dir else self._paths.installs_dir
        self._runtime_root = base_dir / 'runtime' if base_dir else self._paths.runtime_dir
        self._data_root = base_dir / 'data' if base_dir else self._paths.plugin_data_dir


class PluginManager:
    def __init__(..., paths: PluginPaths | None = None) -> None:
        self._paths = paths or build_plugin_paths()
        migrate_legacy_plugin_storage(self._paths)
        self._store = store or PluginInstallStore(paths=self._paths)
        self._installer = installer or PluginInstaller(paths=self._paths)

    def _discover_local_runtime_plugins(self) -> None:
        plugins_root = self._paths.workspace_plugins_dir
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_manager_workspace_sync.py tests/plugins/test_installer.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add squirrel-backend/plugins/installer.py squirrel-backend/plugins/manager.py squirrel-backend/tests/plugins/test_manager_workspace_sync.py squirrel-backend/tests/plugins/test_installer.py
git commit -m "refactor: remove plugin path coupling from manager and installer"
```

### Task 5: Verify integrated behavior

**Files:**
- Modify: `squirrel-backend/tests/plugins/test_manager_workspace_sync.py`
- Modify: `squirrel-backend/tests/plugins/test_store.py`
- Modify: `squirrel-backend/tests/plugins/test_migration.py`

- [ ] **Step 1: Add integrated regression coverage**

```python
def test_manager_uses_migrated_installations_file(...):
    ...


def test_store_write_failure_removes_new_temp_file(...):
    ...
```

- [ ] **Step 2: Run focused backend tests**

Run: `cd squirrel-backend; pipenv run pytest tests/plugins/test_paths.py tests/plugins/test_migration.py tests/plugins/test_store.py tests/plugins/test_installer.py tests/plugins/test_manager_workspace_sync.py -v`
Expected: PASS

- [ ] **Step 3: Run compile check**

Run: `cd squirrel-backend; python -m compileall plugins`
Expected: compile succeeds

- [ ] **Step 4: Commit**

```bash
git add squirrel-backend/plugins squirrel-backend/tests/plugins docs/superpowers/specs/2026-04-07-plugin-runtime-storage-refactor-design.md docs/superpowers/plans/2026-04-07-plugin-runtime-storage-refactor.md
git commit -m "refactor: clean plugin runtime storage layout"
```
