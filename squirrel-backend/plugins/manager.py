from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
import json
from typing import List, Optional

from .gateway import PluginGateway
from .migration import migrate_legacy_plugin_storage
from .models import (
    PluginInstallRecord,
    PluginInstallStatus,
    PluginManagerSnapshot,
)
from .paths import PluginPaths, build_plugin_paths
from .runtime_models import PluginManifest
from .store import PluginInstallStore
from .supervisor import PluginRuntimeSupervisor


class PluginManager:
    """Coordinate plugin records, runtime state, and routing."""

    def __init__(
        self,
        store: Optional[PluginInstallStore] = None,
        supervisor: Optional[PluginRuntimeSupervisor] = None,
        gateway: Optional[PluginGateway] = None,
        paths: PluginPaths | None = None,
    ) -> None:
        self._paths = paths or build_plugin_paths()
        migrate_legacy_plugin_storage(self._paths)
        self._store = store or PluginInstallStore(paths=self._paths)
        self._supervisor = supervisor or PluginRuntimeSupervisor()
        self._gateway = gateway or PluginGateway(invocation_client=self._supervisor)
        self._gateway.set_registration_refresh(self._refresh_gateway_registrations)

    @property
    def gateway(self) -> PluginGateway:
        return self._gateway

    def list_plugins(self) -> List[PluginInstallRecord]:
        return self.discover_plugins()

    def discover_plugins(self) -> List[PluginInstallRecord]:
        return self._discover_local_runtime_plugins()

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        for record in self.discover_plugins():
            if record.plugin_id == plugin_id:
                return record
        return None

    def enable_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        record = self.get_plugin(plugin_id)
        if record is None:
            return None
        record.enabled = True
        record.status = PluginInstallStatus.RUNNING
        self._gateway.register_manifest(
            plugin_id=record.plugin_id,
            version=record.version,
            manifest=PluginManifest.from_dict(record.manifest),
        )
        self._supervisor.start_runtime(record)
        return self._store.upsert(record)

    def disable_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        record = self.get_plugin(plugin_id)
        if record is None:
            return None
        self._gateway.unregister_plugin(plugin_id)
        self._supervisor.stop_runtime(record.plugin_id, record.version)
        record.enabled = False
        record.status = PluginInstallStatus.DISABLED
        return self._store.upsert(record)

    def get_snapshot(self) -> PluginManagerSnapshot:
        records = self.discover_plugins()
        return PluginManagerSnapshot(
            records=records,
            runtimes=self._supervisor.list_handles(),
            registrations=self._gateway.list_registrations(),
        )

    def bootstrap_enabled_plugins(self) -> List[PluginInstallRecord]:
        enabled_records = [record for record in self.discover_plugins() if record.enabled]
        if not enabled_records:
            return []

        for record in enabled_records:
            self._gateway.register_manifest(
                plugin_id=record.plugin_id,
                version=record.version,
                manifest=PluginManifest.from_dict(record.manifest),
            )

        futures: list[tuple[PluginInstallRecord, Future[object]]] = []
        with ThreadPoolExecutor(max_workers=len(enabled_records), thread_name_prefix='plugin-bootstrap') as executor:
            for record in enabled_records:
                futures.append((record, executor.submit(self._supervisor.start_runtime, record)))

            _done, not_done = wait([future for _, future in futures], return_when='FIRST_EXCEPTION')
            if not_done:
                wait(not_done)

        started: List[PluginInstallRecord] = []
        first_error: Exception | None = None
        for record, future in futures:
            try:
                future.result()
            except Exception as exc:  # pragma: no cover - exercised via tests
                if first_error is None:
                    first_error = exc
                continue
            record.status = PluginInstallStatus.RUNNING
            self._store.upsert(record)
            started.append(record)
        if first_error is not None:
            raise first_error
        return started

    def shutdown_all(self) -> None:
        records = self.discover_plugins()
        for record in records:
            handle = self._supervisor.stop_runtime(record.plugin_id, record.version)
            if handle is not None and record.enabled:
                record.status = PluginInstallStatus.STOPPED
                self._store.upsert(record)
        for record in records:
            self._gateway.unregister_plugin(record.plugin_id)

    def reload_enabled_plugins(self) -> List[PluginInstallRecord]:
        self.shutdown_all()
        return self.bootstrap_enabled_plugins()

    def _refresh_gateway_registrations(self) -> None:
        records = self.discover_plugins()
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

    def _discover_local_runtime_plugins(self) -> List[PluginInstallRecord]:
        records_by_id = {
            record.plugin_id: record
            for record in self._store.list_records()
            if record.metadata.get('source') == 'workspace'
        }
        plugins_root = self._paths.workspace_plugins_dir
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

                record = PluginInstallRecord(
                    plugin_id=manifest.plugin_id,
                    version=manifest.version,
                    install_path=str(plugin_root),
                    entrypoint=entrypoint,
                    enabled=True,
                    status=PluginInstallStatus.INSTALLED,
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


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


def bootstrap_plugin_runtime() -> List[PluginInstallRecord]:
    return get_plugin_manager().bootstrap_enabled_plugins()


def shutdown_plugin_runtime() -> None:
    get_plugin_manager().shutdown_all()


def reload_plugin_runtime() -> List[PluginInstallRecord]:
    return get_plugin_manager().reload_enabled_plugins()
