from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class PluginInstallStatus(str, Enum):
    UPLOADED = 'uploaded'
    VALIDATED = 'validated'
    INSTALLED = 'installed'
    STARTING = 'starting'
    RUNNING = 'running'
    DEGRADED = 'degraded'
    DISABLED = 'disabled'
    FAILED = 'failed'
    STOPPED = 'stopped'
    UNINSTALLED = 'uninstalled'


class PluginRuntimeState(str, Enum):
    STARTING = 'starting'
    RUNNING = 'running'
    DRAINING = 'draining'
    STOPPED = 'stopped'
    FAILED = 'failed'


@dataclass
class PluginInstallRecord:
    plugin_id: str
    version: str
    install_path: str
    entrypoint: str
    enabled: bool = False
    status: PluginInstallStatus = PluginInstallStatus.UPLOADED
    granted_permissions: List[str] = field(default_factory=list)
    manifest: Dict[str, Any] = field(default_factory=dict)
    package_path: Optional[str] = None
    runtime_path: Optional[str] = None
    checksum_sha256: Optional[str] = None
    installed_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plugin_id': self.plugin_id,
            'version': self.version,
            'install_path': self.install_path,
            'entrypoint': self.entrypoint,
            'enabled': self.enabled,
            'status': self.status.value,
            'granted_permissions': list(self.granted_permissions),
            'manifest': dict(self.manifest),
            'package_path': self.package_path,
            'runtime_path': self.runtime_path,
            'checksum_sha256': self.checksum_sha256,
            'installed_at': self.installed_at,
            'updated_at': self.updated_at,
            'metadata': dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PluginInstallRecord':
        status = str(data.get('status', PluginInstallStatus.UPLOADED.value))
        try:
            parsed_status = PluginInstallStatus(status)
        except ValueError:
            parsed_status = PluginInstallStatus.FAILED

        return cls(
            plugin_id=str(data.get('plugin_id', '')),
            version=str(data.get('version', '')),
            install_path=str(data.get('install_path', '')),
            entrypoint=str(data.get('entrypoint', '')),
            enabled=bool(data.get('enabled', False)),
            status=parsed_status,
            granted_permissions=list(data.get('granted_permissions') or []),
            manifest=dict(data.get('manifest') or {}),
            package_path=data.get('package_path'),
            runtime_path=data.get('runtime_path'),
            checksum_sha256=data.get('checksum_sha256'),
            installed_at=str(data.get('installed_at', utcnow_iso())),
            updated_at=str(data.get('updated_at', utcnow_iso())),
            metadata=dict(data.get('metadata') or {}),
        )


@dataclass
class PluginHealthSnapshot:
    plugin_id: str
    healthy: bool
    status: str = 'unknown'
    message: str = ''
    checked_at: str = field(default_factory=utcnow_iso)
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginRuntimeHandle:
    plugin_id: str
    version: str
    state: PluginRuntimeState = PluginRuntimeState.STOPPED
    process_id: Optional[int] = None
    endpoint: Optional[str] = None
    started_at: Optional[str] = None
    drained_at: Optional[str] = None
    last_error: Optional[str] = None
    health: Optional[PluginHealthSnapshot] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'plugin_id': self.plugin_id,
            'version': self.version,
            'state': self.state.value,
            'process_id': self.process_id,
            'endpoint': self.endpoint,
            'started_at': self.started_at,
            'drained_at': self.drained_at,
            'last_error': self.last_error,
            'health': None if self.health is None else {
                'plugin_id': self.health.plugin_id,
                'healthy': self.health.healthy,
                'status': self.health.status,
                'message': self.health.message,
                'checked_at': self.health.checked_at,
                'details': dict(self.health.details),
            },
        }


@dataclass
class PluginCapabilityRegistration:
    plugin_id: str
    version: str
    capability: str
    site_name: Optional[str] = None
    domains: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginRoutingTarget:
    plugin_id: str
    version: str
    capability: str
    site_name: Optional[str] = None
    domain: Optional[str] = None


@dataclass
class PluginManagerSnapshot:
    records: List[PluginInstallRecord] = field(default_factory=list)
    runtimes: List[PluginRuntimeHandle] = field(default_factory=list)
    registrations: List[PluginCapabilityRegistration] = field(default_factory=list)
