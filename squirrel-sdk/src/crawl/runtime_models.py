"""Runtime data models for site runtime V2."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .runtime_errors import SiteRuntimeError


@dataclass
class SiteRuntimePermission:
    """Permission declaration required by a plugin."""

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
    """Capability exposed by a site runtime."""

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
    """Site metadata declared by a plugin manifest."""

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
    """Top-level plugin manifest exchanged during runtime handshake."""

    runtime_id: str
    version: str
    sdk_api_version: str = "2.0"
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
            "sdk_api_version": self.sdk_api_version,
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
            sdk_api_version=str(data.get("sdk_api_version", "2.0")),
            display_name=str(data.get("display_name", "")),
            description=str(data.get("description", "")),
            capabilities=[
                item if isinstance(item, SiteRuntimeCapability) else SiteRuntimeCapability.from_dict(item)
                for item in list(data.get("capabilities") or [])
            ],
            sites=[
                item if isinstance(item, SiteRuntimeSite) else SiteRuntimeSite.from_dict(item)
                for item in list(data.get("sites") or [])
            ],
            permissions=[
                item if isinstance(item, SiteRuntimePermission) else SiteRuntimePermission.from_dict(item)
                for item in list(data.get("permissions") or [])
            ],
            config_schema=dict(data.get("config_schema") or {}),
            health_policy=dict(data.get("health_policy") or {}),
            metadata=dict(data.get("metadata") or {}),
            package_name=data.get("package_name"),
            entrypoint=data.get("entrypoint"),
        )


@dataclass
class SiteRuntimeHealthStatus:
    """Health payload returned by site runtimes."""

    healthy: bool
    status: str = "unknown"
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    checked_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeHealthStatus:
        return cls(
            healthy=bool(data.get("healthy", False)),
            status=str(data.get("status", "unknown")),
            message=str(data.get("message", "")),
            details=dict(data.get("details") or {}),
            checked_at=data.get("checked_at"),
        )


@dataclass
class SiteRuntimeInvokeRequest:
    """Invocation request passed from host to site runtime."""

    request_id: str
    capability: str
    payload: dict[str, Any] = field(default_factory=dict)
    site_name: str | None = None
    timeout_ms: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeInvokeRequest:
        return cls(
            request_id=str(data.get("request_id", "")),
            capability=str(data.get("capability", "")),
            payload=dict(data.get("payload") or {}),
            site_name=data.get("site_name"),
            timeout_ms=data.get("timeout_ms"),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SiteRuntimeInvokeResponse:
    """Invocation response returned by site runtime."""

    request_id: str
    ok: bool
    data: Any | None = None
    error: SiteRuntimeError | None = None
    retryable: bool = False
    diagnostics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "request_id": self.request_id,
            "ok": self.ok,
            "data": self.data,
            "error": self.error.to_dict() if self.error else None,
            "retryable": self.retryable,
            "diagnostics": dict(self.diagnostics),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SiteRuntimeInvokeResponse:
        raw_error = data.get("error")
        return cls(
            request_id=str(data.get("request_id", "")),
            ok=bool(data.get("ok", False)),
            data=data.get("data"),
            error=raw_error if isinstance(raw_error, SiteRuntimeError) else (
                SiteRuntimeError.from_dict(raw_error) if isinstance(raw_error, dict) else None
            ),
            retryable=bool(data.get("retryable", False)),
            diagnostics=dict(data.get("diagnostics") or {}),
        )
