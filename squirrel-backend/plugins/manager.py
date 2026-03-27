from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from crawl import PluginManifest

from .gateway import PluginGateway
from .installer import PluginInstaller
from .models import (
    PluginInstallRecord,
    PluginInstallStatus,
    PluginManagerSnapshot,
    utcnow_iso,
)
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
    ) -> None:
        self._store = store or PluginInstallStore()
        self._installer = installer or PluginInstaller()
        self._supervisor = supervisor or PluginRuntimeSupervisor()
        self._gateway = gateway or PluginGateway()

    @property
    def gateway(self) -> PluginGateway:
        return self._gateway

    def list_plugins(self) -> List[PluginInstallRecord]:
        return self._store.list_records()

    def discover_plugins(self) -> List[PluginInstallRecord]:
        return self.list_plugins()

    def get_plugin(self, plugin_id: str) -> Optional[PluginInstallRecord]:
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
        return PluginManagerSnapshot(
            records=self._store.list_records(),
            runtimes=self._supervisor.list_handles(),
            registrations=self._gateway.list_registrations(),
        )
