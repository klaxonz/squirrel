from __future__ import annotations

import logging
import shutil
from pathlib import Path

from .paths import PluginPaths

logger = logging.getLogger(__name__)


def _move_path_if_needed(source: Path, target: Path) -> None:
    if not source.exists():
        return
    if source.is_dir():
        target.mkdir(parents=True, exist_ok=True)
        for child in source.iterdir():
            _move_path_if_needed(child, target / child.name)
        try:
            source.rmdir()
        except OSError:
            logger.warning('Legacy plugin storage directory still contains files after migration: %s', source)
        return
    if target.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))


def migrate_legacy_plugin_storage(paths: PluginPaths) -> bool:
    if paths.installations_file.exists():
        return False
    if not paths.legacy_root.exists():
        return False

    logger.info('Migrating legacy plugin storage from %s to %s', paths.legacy_root, paths.state_dir.parent)

    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.artifacts_dir.mkdir(parents=True, exist_ok=True)
    paths.runtime_dir.mkdir(parents=True, exist_ok=True)
    paths.plugin_data_dir.mkdir(parents=True, exist_ok=True)

    _move_path_if_needed(paths.legacy_root / 'installations.json', paths.installations_file)
    _move_path_if_needed(paths.legacy_root / 'runtime', paths.runtime_dir)
    _move_path_if_needed(paths.legacy_root / 'data', paths.plugin_data_dir)

    for stale in paths.legacy_root.glob('installations.*.tmp'):
        try:
            stale.unlink(missing_ok=True)
        except OSError:
            logger.warning('Failed to remove legacy plugin store temp file: %s', stale)

    return True
