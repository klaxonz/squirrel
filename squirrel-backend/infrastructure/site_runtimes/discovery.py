from __future__ import annotations

import json
from typing import TYPE_CHECKING

from .models import (
    SiteRuntimeDiscoveryError,
    SiteRuntimeDiscoveryResult,
    SiteRuntimeManifest,
    SiteRuntimeRecord,
    SiteRuntimeStatus,
)

if TYPE_CHECKING:
    from .gateway import SiteRuntimeGateway
    from .paths import SiteRuntimePaths
    from .store import SiteRuntimeStore


class SiteRuntimeDiscovery:
    """Discover workspace site runtimes.

    Discovery is split into a pure-read scan and an explicit apply step so
    read paths (listing, snapshot, route resolution) never mutate the store
    or gateway registrations as a side effect.
    """

    def __init__(self, paths: SiteRuntimePaths, store: SiteRuntimeStore, gateway: SiteRuntimeGateway) -> None:
        self._paths = paths
        self._store = store
        self._gateway = gateway

    def scan_workspace(self) -> SiteRuntimeDiscoveryResult:
        """Scan the workspace runtimes dir and return merged records.

        Pure read: merges existing persisted records with what is on disk,
        but does not persist anything or touch gateway registrations.
        """
        existing_by_id = {
            record.runtime_id: record
            for record in self._store.list_records()
            if record.metadata.get('source') == 'workspace'
        }
        records_by_id: dict[str, SiteRuntimeRecord] = {}
        errors: list[SiteRuntimeDiscoveryError] = []
        runtimes_root = self._paths.workspace_runtimes_dir
        if not runtimes_root.exists():
            return SiteRuntimeDiscoveryResult(records=[], errors=[])

        for metadata_path in runtimes_root.glob('*/site-runtime.json'):
            try:
                payload = json.loads(metadata_path.read_text(encoding='utf-8'))
                manifest_payload = payload.get('manifest') or {}
                entrypoint = str(payload.get('entrypoint', '')).strip()
                manifest = SiteRuntimeManifest.from_dict(manifest_payload)
                if not manifest.runtime_id or not entrypoint:
                    errors.append(SiteRuntimeDiscoveryError(
                        metadata_path=str(metadata_path),
                        reason='missing runtime_id or entrypoint',
                    ))
                    continue

                runtime_root = metadata_path.parent
                runtime_path = runtime_root / 'src'
                existing = existing_by_id.get(manifest.runtime_id)
                if existing is not None:
                    existing.version = manifest.version
                    existing.install_path = str(runtime_root)
                    existing.entrypoint = entrypoint
                    existing.granted_permissions = [item.name for item in manifest.permissions]
                    existing.manifest = manifest.to_dict()
                    existing.package_path = str(metadata_path)
                    existing.runtime_path = str(runtime_path if runtime_path.exists() else runtime_root)
                    existing.metadata = {'source': 'workspace'}
                    records_by_id[existing.runtime_id] = existing
                    continue

                record = SiteRuntimeRecord(
                    runtime_id=manifest.runtime_id,
                    version=manifest.version,
                    install_path=str(runtime_root),
                    entrypoint=entrypoint,
                    enabled=True,
                    status=SiteRuntimeStatus.INSTALLED,
                    granted_permissions=[item.name for item in manifest.permissions],
                    manifest=manifest.to_dict(),
                    package_path=str(metadata_path),
                    runtime_path=str(runtime_path if runtime_path.exists() else runtime_root),
                    metadata={'source': 'workspace'},
                )
                records_by_id[record.runtime_id] = record
            except Exception as exc:
                errors.append(SiteRuntimeDiscoveryError(
                    metadata_path=str(metadata_path),
                    reason=str(exc),
                ))
        return SiteRuntimeDiscoveryResult(
            records=sorted(records_by_id.values(), key=lambda record: record.runtime_id.lower()),
            errors=errors,
        )

    def apply_discovery_result(self, result: SiteRuntimeDiscoveryResult) -> SiteRuntimeDiscoveryResult:
        """Persist discovery result and remove stale workspace records.

        Write path: upserts every record into the store. Must only be called
        from explicit write entry points, never from read paths.
        """
        existing_workspace_ids = {
            record.runtime_id
            for record in self._store.list_records()
            if record.metadata.get('source') == 'workspace'
        }
        discovered_ids = {record.runtime_id for record in result.records}
        for runtime_id in existing_workspace_ids - discovered_ids:
            self._store.delete(runtime_id)
            self._gateway.unregister_plugin(runtime_id)

        persisted: list[SiteRuntimeRecord] = []
        for record in result.records:
            before = self._store.get_record(record.runtime_id)
            before_dict = before.to_dict() if before is not None else None
            new_dict = record.to_dict()
            # Mask updated_at when comparing — it always changes on upsert.
            if before_dict is not None:
                before_dict['updated_at'] = new_dict.get('updated_at')
            changed = before_dict != new_dict

            upserted = self._store.upsert(record) if changed else record
            persisted.append(upserted)

        return SiteRuntimeDiscoveryResult(records=persisted, errors=list(result.errors))
