from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


def utcnow_iso() -> str:
    return datetime.now(UTC).isoformat()


class SiteRuntimeStatus(StrEnum):
    VALIDATED = "validated"
    INSTALLED = "installed"
    STARTING = "starting"
    RUNNING = "running"
    DEGRADED = "degraded"
    DISABLED = "disabled"
    FAILED = "failed"
    STOPPED = "stopped"


class SiteRuntimeState(StrEnum):
    STARTING = "starting"
    RUNNING = "running"
    DRAINING = "draining"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class SiteRuntimeRecord:
    runtime_id: str
    version: str
    install_path: str
    entrypoint: str
    enabled: bool = False
    status: SiteRuntimeStatus = SiteRuntimeStatus.INSTALLED
    granted_permissions: list[str] = field(default_factory=list)
    manifest: dict[str, Any] = field(default_factory=dict)
    package_path: str | None = None
    runtime_path: str | None = None
    data_path: str | None = None
    checksum_sha256: str | None = None
    installed_at: str = field(default_factory=utcnow_iso)
    updated_at: str = field(default_factory=utcnow_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "version": self.version,
            "install_path": self.install_path,
            "entrypoint": self.entrypoint,
            "enabled": self.enabled,
            "status": self.status.value,
            "granted_permissions": list(self.granted_permissions),
            "manifest": dict(self.manifest),
            "package_path": self.package_path,
            "runtime_path": self.runtime_path,
            "data_path": self.data_path,
            "checksum_sha256": self.checksum_sha256,
            "installed_at": self.installed_at,
            "updated_at": self.updated_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeRecord:
        status = str(data.get("status", SiteRuntimeStatus.INSTALLED.value))
        try:
            parsed_status = SiteRuntimeStatus(status)
        except ValueError:
            parsed_status = SiteRuntimeStatus.FAILED

        return cls(
            runtime_id=str(data.get("runtime_id", "")),
            version=str(data.get("version", "")),
            install_path=str(data.get("install_path", "")),
            entrypoint=str(data.get("entrypoint", "")),
            enabled=bool(data.get("enabled", False)),
            status=parsed_status,
            granted_permissions=list(data.get("granted_permissions") or []),
            manifest=dict(data.get("manifest") or {}),
            package_path=data.get("package_path"),
            runtime_path=data.get("runtime_path"),
            data_path=data.get("data_path"),
            checksum_sha256=data.get("checksum_sha256"),
            installed_at=str(data.get("installed_at", utcnow_iso())),
            updated_at=str(data.get("updated_at", utcnow_iso())),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SiteRuntimeHealthSnapshot:
    runtime_id: str
    healthy: bool
    status: str = "unknown"
    message: str = ""
    checked_at: str = field(default_factory=utcnow_iso)
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteRuntimeHandle:
    runtime_id: str
    version: str
    state: SiteRuntimeState = SiteRuntimeState.STOPPED
    process_id: int | None = None
    endpoint: str | None = None
    started_at: str | None = None
    drained_at: str | None = None
    last_error: str | None = None
    health: SiteRuntimeHealthSnapshot | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "version": self.version,
            "state": self.state.value,
            "process_id": self.process_id,
            "endpoint": self.endpoint,
            "started_at": self.started_at,
            "drained_at": self.drained_at,
            "last_error": self.last_error,
            "health": None if self.health is None else {
                "runtime_id": self.health.runtime_id,
                "healthy": self.health.healthy,
                "status": self.health.status,
                "message": self.health.message,
                "checked_at": self.health.checked_at,
                "details": dict(self.health.details),
            },
        }


@dataclass
class SiteCapabilityRegistration:
    runtime_id: str
    version: str
    capability: str
    site_name: str | None = None
    domains: list[str] = field(default_factory=list)
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SiteRuntimeTarget:
    runtime_id: str
    version: str
    capability: str
    site_name: str | None = None
    domain: str | None = None


@dataclass
class SiteRuntimeSnapshot:
    records: list[SiteRuntimeRecord] = field(default_factory=list)
    runtimes: list[SiteRuntimeHandle] = field(default_factory=list)
    registrations: list[SiteCapabilityRegistration] = field(default_factory=list)
    discovery_errors: list[SiteRuntimeDiscoveryError] = field(default_factory=list)


@dataclass
class SiteRuntimeDiscoveryError:
    metadata_path: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {
            "metadata_path": self.metadata_path,
            "reason": self.reason,
        }


@dataclass
class SiteRuntimeDiscoveryResult:
    records: list[SiteRuntimeRecord] = field(default_factory=list)
    errors: list[SiteRuntimeDiscoveryError] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Manifest DTOs (merged from runtime_models.py)
# ---------------------------------------------------------------------------


@dataclass
class SiteRuntimePermission:
    name: str
    description: str = ""
    required: bool = True
    scope: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimePermission:
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            required=bool(data.get("required", True)),
            scope=data.get("scope"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SiteRuntimeCapability:
    name: str
    description: str = ""
    request_schema: dict[str, Any] = field(default_factory=dict)
    response_schema: dict[str, Any] = field(default_factory=dict)
    timeout_ms: int | None = None
    requires: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeCapability:
        return cls(
            name=str(data.get("name", "")),
            description=str(data.get("description", "")),
            request_schema=dict(data.get("request_schema") or {}),
            response_schema=dict(data.get("response_schema") or {}),
            timeout_ms=data.get("timeout_ms"),
            requires=list(data.get("requires") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SiteRuntimeSite:
    site_name: str
    domains: list[str] = field(default_factory=list)
    test_url: str | None = None
    features: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeSite:
        return cls(
            site_name=str(data.get("site_name", "")),
            domains=list(data.get("domains") or []),
            test_url=data.get("test_url"),
            features=list(data.get("features") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SiteRuntimeManifest:
    runtime_id: str
    version: str
    runtime_api_version: str = "2.0"
    display_name: str = ""
    description: str = ""
    capabilities: list[SiteRuntimeCapability] = field(default_factory=list)
    sites: list[SiteRuntimeSite] = field(default_factory=list)
    permissions: list[SiteRuntimePermission] = field(default_factory=list)
    config_schema: dict[str, Any] = field(default_factory=dict)
    health_policy: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    package_name: str | None = None
    entrypoint: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "runtime_id": self.runtime_id,
            "version": self.version,
            "runtime_api_version": self.runtime_api_version,
            "display_name": self.display_name,
            "description": self.description,
            "capabilities": [item.to_dict() for item in self.capabilities],
            "sites": [item.to_dict() for item in self.sites],
            "permissions": [item.to_dict() for item in self.permissions],
            "config_schema": dict(self.config_schema),
            "health_policy": dict(self.health_policy),
            "metadata": dict(self.metadata),
            "package_name": self.package_name,
            "entrypoint": self.entrypoint,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeManifest:
        return cls(
            runtime_id=str(data.get("runtime_id", "")),
            version=str(data.get("version", "")),
            runtime_api_version=str(data.get("runtime_api_version", "2.0")),
            display_name=str(data.get("display_name", "")),
            description=str(data.get("description", "")),
            capabilities=[SiteRuntimeCapability.from_dict(item) for item in list(data.get("capabilities") or [])],
            sites=[SiteRuntimeSite.from_dict(item) for item in list(data.get("sites") or [])],
            permissions=[SiteRuntimePermission.from_dict(item) for item in list(data.get("permissions") or [])],
            config_schema=dict(data.get("config_schema") or {}),
            health_policy=dict(data.get("health_policy") or {}),
            metadata=dict(data.get("metadata") or {}),
            package_name=data.get("package_name"),
            entrypoint=data.get("entrypoint"),
        )
