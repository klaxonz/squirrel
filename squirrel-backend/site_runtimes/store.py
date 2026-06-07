from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from .models import SiteRuntimeRecord, SiteRuntimeStatus, utcnow_iso
from .paths import SiteRuntimePaths, build_site_runtime_paths

logger = logging.getLogger(__name__)


class SiteRuntimeStore:
    """Persist site runtime records as JSON."""

    def __init__(self, data_path: Path | None = None, paths: SiteRuntimePaths | None = None) -> None:
        self._paths = paths or build_site_runtime_paths()
        self._data_path = data_path or self._paths.records_file
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        self._cleanup_stale_temp_files()

    @property
    def data_path(self) -> Path:
        return self._data_path

    def _load_raw(self) -> dict[str, dict]:
        if not self._data_path.exists():
            return {}
        raw_text = self._data_path.read_text(encoding="utf-8")
        if not raw_text.strip():
            return {}
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            logger.warning("Site runtime store is unreadable, treating it as empty: %s", exc)
            return {}
        if not isinstance(payload, dict):
            return {}
        return payload

    def _save_raw(self, records: dict[str, dict]) -> None:
        self._data_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self._data_path.parent,
                delete=False,
                prefix=f"{self._data_path.stem}.",
                suffix=".tmp",
            ) as handle:
                json.dump(records, handle, ensure_ascii=False, indent=2, sort_keys=True)
                handle.flush()
                os.fsync(handle.fileno())
                temp_path = Path(handle.name)
            os.replace(temp_path, self._data_path)
        except OSError:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except OSError:
                    logger.warning("Failed to remove site runtime store temp file after write failure: %s", temp_path)
            raise

    def _cleanup_stale_temp_files(self) -> None:
        pattern = f"{self._data_path.stem}.*.tmp"
        for candidate in self._data_path.parent.glob(pattern):
            try:
                candidate.unlink(missing_ok=True)
            except OSError:
                logger.warning("Failed to remove stale site runtime store temp file: %s", candidate)

    def list_records(self) -> list[SiteRuntimeRecord]:
        payload = self._load_raw()
        return [
            SiteRuntimeRecord.from_dict(item)
            for _, item in sorted(payload.items(), key=lambda entry: entry[0].lower())
        ]

    def get_record(self, runtime_id: str) -> SiteRuntimeRecord | None:
        payload = self._load_raw()
        item = payload.get(runtime_id)
        if item is None:
            return None
        return SiteRuntimeRecord.from_dict(item)

    def upsert(self, record: SiteRuntimeRecord) -> SiteRuntimeRecord:
        payload = self._load_raw()
        record.updated_at = utcnow_iso()
        payload[record.runtime_id] = record.to_dict()
        self._save_raw(payload)
        return record

    def delete(self, runtime_id: str) -> None:
        payload = self._load_raw()
        if runtime_id in payload:
            del payload[runtime_id]
            self._save_raw(payload)

    def set_enabled(self, runtime_id: str, enabled: bool) -> SiteRuntimeRecord | None:
        record = self.get_record(runtime_id)
        if record is None:
            return None
        record.enabled = enabled
        if enabled and record.status == SiteRuntimeStatus.DISABLED:
            record.status = SiteRuntimeStatus.INSTALLED
        if not enabled:
            record.status = SiteRuntimeStatus.DISABLED
        return self.upsert(record)



