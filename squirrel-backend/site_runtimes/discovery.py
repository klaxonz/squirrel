from __future__ import annotations

import json

from .gateway import SiteRuntimeGateway
from .models import SiteRuntimeDiscoveryError, SiteRuntimeDiscoveryResult, SiteRuntimeRecord, SiteRuntimeStatus
from .paths import SiteRuntimePaths
from .runtime_models import SiteRuntimeManifest
from .store import SiteRuntimeStore


class SiteRuntimeDiscovery:
    """Discover workspace site runtimes and synchronize store records."""

    def __init__(self, paths: SiteRuntimePaths, store: SiteRuntimeStore, gateway: SiteRuntimeGateway) -> None:
        self._paths = paths
        self._store = store
        self._gateway = gateway

    def discover_workspace_site_runtimes(self) -> SiteRuntimeDiscoveryResult:
        records_by_id = {
            record.runtime_id: record
            for record in self._store.list_records()
            if record.metadata.get('source') == 'workspace'
        }
        errors: list[SiteRuntimeDiscoveryError] = []
        runtimes_root = self._paths.workspace_runtimes_dir
        if not runtimes_root.exists():
            return SiteRuntimeDiscoveryResult(
                records=sorted(records_by_id.values(), key=lambda record: record.runtime_id.lower()),
                errors=[],
            )

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
                existing = records_by_id.get(manifest.runtime_id)
                if existing is not None:
                    before = existing.to_dict()
                    existing.version = manifest.version
                    existing.install_path = str(runtime_root)
                    existing.entrypoint = entrypoint
                    existing.granted_permissions = [item.name for item in manifest.permissions]
                    existing.manifest = manifest.to_dict()
                    existing.package_path = str(metadata_path)
                    existing.runtime_path = str(runtime_path if runtime_path.exists() else runtime_root)
                    existing.metadata = {'source': 'workspace'}
                    after = existing.to_dict()
                    after['updated_at'] = before.get('updated_at')
                    if after != before:
                        records_by_id[existing.runtime_id] = self._store.upsert(existing)

                    if existing.enabled and after != before:
                        self._gateway.unregister_plugin(existing.runtime_id)
                        self._gateway.register_manifest(
                            runtime_id=existing.runtime_id,
                            version=existing.version,
                            manifest=SiteRuntimeManifest.from_dict(existing.manifest),
                        )
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
                records_by_id[record.runtime_id] = self._store.upsert(record)
            except Exception as exc:
                errors.append(SiteRuntimeDiscoveryError(
                    metadata_path=str(metadata_path),
                    reason=str(exc),
                ))
        return SiteRuntimeDiscoveryResult(
            records=sorted(records_by_id.values(), key=lambda record: record.runtime_id.lower()),
            errors=errors,
        )
