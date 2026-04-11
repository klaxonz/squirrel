from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor, wait
import json
from pathlib import Path
from typing import List, Optional

from .gateway import PluginGateway
from .installer import PluginInstaller
from .migration import migrate_legacy_plugin_storage
from .models import (
    PluginInstallRecord,
    PluginInstallStatus,
    PluginManagerSnapshot,
    utcnow_iso,
)
from .paths import PluginPaths, build_plugin_paths
from .runtime_models import PluginManifest
from .store import PluginInstallStore
from .supervisor import PluginRuntimeSupervisor


class PluginManager:
    """Coordinate plugin installation records, runtime state, and routing."""

    def __init__(
        self,
        store: Optional[PluginInstallStore] = None,
        installer: Optional[PluginInstaller] = None,
        supervisor: Optional[PluginRuntimeSupervisor] = None,
        gateway: Optional[PluginGateway] = None,
        paths: PluginPaths | None = None,
    ) -> None:
        self._paths = paths or build_plugin_paths()
        migrate_legacy_plugin_storage(self._paths)
        self._store = store or PluginInstallStore(paths=self._paths)
        self._installer = installer or PluginInstaller(paths=self._paths)
        self._supervisor = supervisor or PluginRuntimeSupervisor()
        self._gateway = gateway or PluginGateway(invocation_client=self._supervisor)
        self._gateway.set_registration_refresh(self._refresh_gateway_registrations)

    @property
    def gateway(self) -> PluginGateway:
        return self._gateway

    def list_plugins(self) -> List[PluginInstallRecord]:
        self.discover_plugins()
        return self._store.list_records()

    def discover_plugins(self) -> List[PluginInstallRecord]:
        self._discover_local_runtime_plugins()
        return self._store.list_records()

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        self.discover_plugins()
        return self._store.get_record(plugin_id)

    def install_plugin(
        self,
        package_path: Path | str,
        manifest: PluginManifest,
        entrypoint: str,
        granted_permissions: Optional[List[str]] = None,
        replace_existing: bool = False,
    ) -> PluginInstallRecord:
        plan = self._installer.build_install_plan(
            package_path=package_path,
            manifest=manifest,
            entrypoint=entrypoint,
            replace_existing=replace_existing,
        )
        self._installer.stage_distribution(plan)
        runtime_env_path, runtime_python = self._installer.provision_runtime_environment(plan)
        record = PluginInstallRecord(
            plugin_id=plan.plugin_id,
            version=plan.version,
            install_path=str(plan.install_path),
            entrypoint=plan.entrypoint,
            enabled=False,
            status=PluginInstallStatus.INSTALLED,
            granted_permissions=list(granted_permissions or []),
            manifest=plan.manifest.to_dict(),
            package_path=str(plan.staging_path),
            runtime_path=str(plan.runtime_path),
            runtime_env_path=str(runtime_env_path),
            runtime_python=str(runtime_python),
            data_path=str(plan.data_path),
            checksum_sha256=plan.checksum_sha256,
            installed_at=utcnow_iso(),
            updated_at=utcnow_iso(),
        )
        self._store.upsert(record)
        self._supervisor.register_placeholder(record)
        return record

    def enable_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        record = self._store.get_record(plugin_id)
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
        record = self._store.get_record(plugin_id)
        if record is None:
            return None
        self._gateway.unregister_plugin(plugin_id)
        self._supervisor.stop_runtime(record.plugin_id, record.version)
        record.enabled = False
        record.status = PluginInstallStatus.DISABLED
        return self._store.upsert(record)

    def uninstall_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
        record = self._store.get_record(plugin_id)
        if record is None:
            return None
        self.disable_plugin(plugin_id)
        if record.metadata.get('source') != 'workspace':
            self._installer.remove_runtime_environment(record.runtime_env_path)
            self._installer.remove_installation(record.install_path)
            self._installer.remove_installation(record.data_path)
        record.status = PluginInstallStatus.UNINSTALLED
        record.enabled = False
        self._store.delete(plugin_id)
        return record

    def upgrade_plugin(
        self,
        plugin_id: str,
        package_path: Path | str,
        manifest: PluginManifest,
        entrypoint: str,
        granted_permissions: Optional[List[str]] = None,
    ) -> PluginInstallRecord:
        existing = self._store.get_record(plugin_id)
        if existing is not None:
            self.disable_plugin(plugin_id)
        return self.install_plugin(
            package_path=package_path,
            manifest=manifest,
            entrypoint=entrypoint,
            granted_permissions=granted_permissions,
            replace_existing=existing is not None,
        )

    def get_snapshot(self) -> PluginManagerSnapshot:
        self.discover_plugins()
        return PluginManagerSnapshot(
            records=self._store.list_records(),
            runtimes=self._supervisor.list_handles(),
            registrations=self._gateway.list_registrations(),
        )

    def bootstrap_enabled_plugins(self) -> List[PluginInstallRecord]:
        self.discover_plugins()
        enabled_records = [record for record in self._store.list_records() if record.enabled]
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
        records = self._store.list_records()
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
        self.discover_plugins()
        existing_plugin_ids = {registration.plugin_id for registration in self._gateway.list_registrations()}
        active_plugin_ids: set[str] = set()

        for record in self._store.list_records():
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

    def _discover_local_runtime_plugins(self) -> None:
        plugins_root = self._paths.workspace_plugins_dir
        if not plugins_root.exists():
            return

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
                existing = self._store.get_record(manifest.plugin_id)
                if existing is not None:
                    if existing.metadata.get('source') != 'workspace':
                        continue

                    existing.version = manifest.version
                    existing.install_path = str(plugin_root)
                    existing.entrypoint = entrypoint
                    existing.granted_permissions = [item.name for item in manifest.permissions]
                    existing.manifest = manifest.to_dict()
                    existing.package_path = str(metadata_path)
                    existing.runtime_path = str(runtime_path if runtime_path.exists() else plugin_root)
                    existing.metadata = {'source': 'workspace'}
                    self._store.upsert(existing)
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
                self._store.upsert(record)
            except Exception:
                continue


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
