from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from .models import SiteRuntimeRecord, utcnow_iso


class SiteRuntimeAuditWriter:
    def __init__(self, backend_root: Path) -> None:
        self._backend_root = backend_root

    def resolve_artifact_paths(self, record: SiteRuntimeRecord) -> dict[str, Path]:
        base_dir = Path(record.data_path or record.install_path or self._backend_root)
        log_dir = base_dir / 'runtime-logs'
        audit_dir = base_dir / 'runtime-audit'
        return {
            'log_dir': log_dir,
            'stdout': log_dir / 'stdout.log',
            'stderr': log_dir / 'stderr.log',
            'audit': audit_dir / 'audit.jsonl',
        }

    def append_event(self, record: SiteRuntimeRecord, event: str, details: Optional[dict] = None) -> Path:
        artifact_paths = self.resolve_artifact_paths(record)
        audit_path = artifact_paths['audit']
        audit_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            'timestamp': utcnow_iso(),
            'runtime_id': record.runtime_id,
            'version': record.version,
            'event': event,
            'details': dict(details or {}),
        }
        with audit_path.open('a', encoding='utf-8') as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + '\n')
        return audit_path
