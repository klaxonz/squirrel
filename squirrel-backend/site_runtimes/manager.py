from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
import json
from typing import List, Optional

from .gateway import SiteRuntimeGateway
from .migration import migrate_legacy_site_runtime_storage
from .models import (
    SiteRuntimeRecord,
    SiteRuntimeStatus,
    SiteRuntimeSnapshot,
)
from .paths import SiteRuntimePaths, build_site_runtime_paths
from .runtime_models import PluginManifest
from .store import SiteRuntimeStore
from .supervisor import SiteRuntimeSupervisor


class SiteRuntimeManager:
    """Coordinate site runtime records, runtime state, and routing."""

    def __init__(
        self,
        store: Optional[SiteRuntimeStore] = None,
        supervisor: Optional[SiteRuntimeSupervisor] = None,
        gateway: Optional[SiteRuntimeGateway] = None,
        paths: SiteRuntimePaths | None = None,
    ) -> None:
        self._paths = paths or build_site_runtime_paths()
        migrate_legacy_site_runtime_storage(self._paths)
        self._store = store or SiteRuntimeStore(paths=self._paths)
        self._supervisor = supervisor or SiteRuntimeSupervisor()
        self._gateway = gateway or SiteRuntimeGateway(invocation_client=self._supervisor)
        self._gateway.set_registration_refresh(self._refresh_gateway_registrations)

    @property
    def gateway(self) -> SiteRuntimeGateway:
        return self._gateway

    def list_site_runtimes(self) -> List[SiteRuntimeRecord]:
        return self.discover_site_runtimes()

    def discover_site_runtimes(self) -> List[SiteRuntimeRecord]:
        return self._discover_local_runtime_plugins()

    def get_site_runtime(self, plugin_id: str) -> Optional[SiteRuntimeRecord]:
        for record in self.discover_site_runtimes():
            if record.plugin_id == plugin_id:
                return record
        return None

    def enable_site_runtime(self, plugin_id: str) -> Optional[SiteRuntimeRecord]:
        record = self.get_site_runtime(plugin_id)
        if record is None:
            return None
        record.enabled = True
        record.status = SiteRuntimeStatus.RUNNING
        self._gateway.register_manifest(
            plugin_id=record.plugin_id,
            version=record.version,
            manifest=PluginManifest.from_dict(record.manifest),
        )
        self._supervisor.start_runtime(record)
        return self._store.upsert(record)

    def disable_site_runtime(self, plugin_id: str) -> Optional[SiteRuntimeRecord]:
        record = self.get_site_runtime(plugin_id)
        if record is None:
            return None
        self._gateway.unregister_plugin(plugin_id)
        self._supervisor.stop_runtime(record.plugin_id, record.version)
        record.enabled = False
        record.status = SiteRuntimeStatus.DISABLED
        return self._store.upsert(record)

    def get_snapshot(self) -> SiteRuntimeSnapshot:
        records = self.discover_site_runtimes()
        return SiteRuntimeSnapshot(
            records=records,
            runtimes=self._supervisor.list_handles(),
            registrations=self._gateway.list_registrations(),
        )

    def bootstrap_enabled_site_runtimes(self) -> List[SiteRuntimeRecord]:
        enabled_records = [record for record in self.discover_site_runtimes() if record.enabled]
        if not enabled_records:
            return []

        for record in enabled_records:
            self._gateway.register_manifest(
                plugin_id=record.plugin_id,
                version=record.version,
                manifest=PluginManifest.from_dict(record.manifest),
            )

        futures: list[tuple[SiteRuntimeRecord, Future[object]]] = []
        with ThreadPoolExecutor(max_workers=len(enabled_records), thread_name_prefix='site-runtime-bootstrap') as executor:
            for record in enabled_records:
                futures.append((record, executor.submit(self._supervisor.start_runtime, record)))

            _done, not_done = wait([future for _, future in futures], return_when='FIRST_EXCEPTION')
            if not_done:
                wait(not_done)

        started: List[SiteRuntimeRecord] = []
        first_error: Exception | None = None
        for record, future in futures:
            try:
                future.result()
            except Exception as exc:  # pragma: no cover - exercised via tests
                if first_error is None:
                    first_error = exc
                continue
            record.status = SiteRuntimeStatus.RUNNING
            self._store.upsert(record)
            started.append(record)
        if first_error is not None:
            raise first_error
        return started

    def shutdown_all(self) -> None:
        records = self.discover_site_runtimes()
        for record in records:
            handle = self._supervisor.stop_runtime(record.plugin_id, record.version)
            if handle is not None and record.enabled:
                record.status = SiteRuntimeStatus.STOPPED
                self._store.upsert(record)
        for record in records:
            self._gateway.unregister_plugin(record.plugin_id)

    def reload_enabled_site_runtimes(self) -> List[SiteRuntimeRecord]:
        self.shutdown_all()
        return self.bootstrap_enabled_site_runtimes()

    def _refresh_gateway_registrations(self) -> None:
        records = self.discover_site_runtimes()
        existing_plugin_ids = {registration.plugin_id for registration in self._gateway.list_registrations()}
        active_plugin_ids: set[str] = set()

        for record in records:
            active_plugin_ids.add(record.plugin_id)
            if not record.enabled:
                self._gateway.unregister_plugin(record.plugin_id)
                continue
            self._gateway.register_manifest(
                plugin_id=record.plugin_id,
                version=record.version,
                manifest=PluginManifest.from_dict(record.manifest),
            )

        for plugin_id in existing_plugin_ids - active_plugin_ids:
            self._gateway.unregister_plugin(plugin_id)

    def _discover_local_runtime_plugins(self) -> List[SiteRuntimeRecord]:
        records_by_id = {
            record.plugin_id: record
            for record in self._store.list_records()
            if record.metadata.get('source') == 'workspace'
        }
        plugins_root = self._paths.workspace_runtimes_dir
        if not plugins_root.exists():
            return sorted(records_by_id.values(), key=lambda record: record.plugin_id.lower())

        for metadata_path in plugins_root.glob('*/plugin-runtime.json'):
            try:
                payload = json.loads(metadata_path.read_text(encoding='utf-8'))
                manifest_payload = payload.get('manifest') or {}
                entrypoint = str(payload.get('entrypoint', '')).strip()
                manifest = PluginManifest.from_dict(manifest_payload)
                if not manifest.plugin_id or not entrypoint:
                    continue

                plugin_root = metadata_path.parent
                runtime_path = plugin_root / 'src'
                existing = records_by_id.get(manifest.plugin_id)
                if existing is not None:
                    before = existing.to_dict()
                    existing.version = manifest.version
                    existing.install_path = str(plugin_root)
                    existing.entrypoint = entrypoint
                    existing.granted_permissions = [item.name for item in manifest.permissions]
                    existing.manifest = manifest.to_dict()
                    existing.package_path = str(metadata_path)
                    existing.runtime_path = str(runtime_path if runtime_path.exists() else plugin_root)
                    existing.metadata = {'source': 'workspace'}
                    after = existing.to_dict()
                    after['updated_at'] = before.get('updated_at')
                    if after != before:
                        records_by_id[existing.plugin_id] = self._store.upsert(existing)

                    if existing.enabled and after != before:
                        self._gateway.unregister_plugin(existing.plugin_id)
                        self._gateway.register_manifest(
                            plugin_id=existing.plugin_id,
                            version=existing.version,
                            manifest=PluginManifest.from_dict(existing.manifest),
                        )
                    continue

                record = SiteRuntimeRecord(
                    plugin_id=manifest.plugin_id,
                    version=manifest.version,
                    install_path=str(plugin_root),
                    entrypoint=entrypoint,
                    enabled=True,
                    status=SiteRuntimeStatus.INSTALLED,
                    granted_permissions=[item.name for item in manifest.permissions],
                    manifest=manifest.to_dict(),
                    package_path=str(metadata_path),
                    runtime_path=str(runtime_path if runtime_path.exists() else plugin_root),
                    metadata={'source': 'workspace'},
                )
                records_by_id[record.plugin_id] = self._store.upsert(record)
            except Exception:
                continue
        return sorted(records_by_id.values(), key=lambda record: record.plugin_id.lower())


_site_runtime_manager: Optional[SiteRuntimeManager] = None


def get_site_runtime_manager() -> SiteRuntimeManager:
    global _site_runtime_manager
    if _site_runtime_manager is None:
        _site_runtime_manager = SiteRuntimeManager()
    return _site_runtime_manager


def bootstrap_site_runtimes() -> List[SiteRuntimeRecord]:
    return get_site_runtime_manager().bootstrap_enabled_site_runtimes()


def shutdown_site_runtimes() -> None:
    get_site_runtime_manager().shutdown_all()


def reload_site_runtimes() -> List[SiteRuntimeRecord]:
    return get_site_runtime_manager().reload_enabled_site_runtimes()



