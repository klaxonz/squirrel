from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from core.config import settings

from .models import PluginInstallRecord, PluginInstallStatus, utcnow_iso


class PluginInstallStore:
    """Persist plugin runtime installation records as JSON."""

    def __init__(self, data_path: Optional[Path] = None) -> None:
        base_path = settings.config_dir / 'plugin_runtime_v2'
        self._data_path = data_path or (base_path / 'installations.json')
        self._data_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def data_path(self) -> Path:
        return self._data_path

    def _load_raw(self) -> Dict[str, Dict]:
        if not self._data_path.exists():
            return {}
        with self._data_path.open('r', encoding='utf-8') as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return {}
        return payload

    def _save_raw(self, records: Dict[str, Dict]) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        with self._data_path.open('w', encoding='utf-8') as handle:
            json.dump(records, handle, ensure_ascii=False, indent=2, sort_keys=True)

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
