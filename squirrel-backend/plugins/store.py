from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import tempfile
from typing import Dict, List, Optional

from .models import PluginInstallRecord, PluginInstallStatus, utcnow_iso
from .paths import PluginPaths, build_plugin_paths

logger = logging.getLogger(__name__)


class PluginInstallStore:
    """Persist plugin runtime records as JSON."""

    def __init__(self, data_path: Optional[Path] = None, paths: PluginPaths | None = None) -> None:
        self._paths = paths or build_plugin_paths()
        self._data_path = data_path or self._paths.installations_file
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_temp_files()

    @property
    def data_path(self) -> Path:
        return self._data_path

    def _load_raw(self) -> Dict[str, Dict]:
        if not self._data_path.exists():
            return {}
        raw_text = self._data_path.read_text(encoding='utf-8')
        if not raw_text.strip():
            return {}
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning('Plugin installation store is unreadable, treating it as empty: %s', exc)
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _save_raw(self, records: Dict[str, Dict]) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                'w',
                encoding='utf-8',
                dir=self._data_path.parent,
                delete=False,
                prefix=f'{self._data_path.stem}.',
                suffix='.tmp',
            ) as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)
            os.replace(temp_path, self._data_path)
        except Exception:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning('Failed to remove plugin store temp file after write failure: %s', temp_path)
            raise

    def _cleanup_stale_temp_files(self) -> None:
        pattern = f'{self._data_path.stem}.*.tmp'
        for candidate in self._data_path.parent.glob(pattern):
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                logger.warning('Failed to remove stale plugin store temp file: %s', candidate)

    def list_records(self) -> List[PluginInstallRecord]:
        payload = self._load_raw()
        return [
            PluginInstallRecord.from_dict(item)
            for _, item in sorted(payload.items(), key=lambda entry: entry[0].lower())
        ]

    def get_record(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        payload = self._load_raw()
        item = payload.get(plugin_id)
        if item is None:
            return None
        return PluginInstallRecord.from_dict(item)

    def upsert(self, record: PluginInstallRecord) -> PluginInstallRecord:
        payload = self._load_raw()
        record.updated_at = utcnow_iso()
        payload[record.plugin_id] = record.to_dict()
        self._save_raw(payload)
        return record

    def delete(self, plugin_id: str) -> None:
        payload = self._load_raw()
        if plugin_id in payload:
            del payload[plugin_id]
            self._save_raw(payload)

    def set_enabled(self, plugin_id: str, enabled: bool) -> Optional[PluginInstallRecord]:
        record = self.get_record(plugin_id)
        if record is None:
            return None
        record.enabled = enabled
        if enabled and record.status == PluginInstallStatus.DISABLED:
            record.status = PluginInstallStatus.INSTALLED
        if not enabled:
            record.status = PluginInstallStatus.DISABLED
        return self.upsert(record)
