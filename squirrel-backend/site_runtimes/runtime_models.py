from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SiteRuntimePermission:
    name: str
    description: str = ''
    required: bool = True
    scope: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SiteRuntimePermission':
        return cls(
            name=str(data.get('name', '')),
            description=str(data.get('description', '')),
            required=bool(data.get('required', True)),
            scope=data.get('scope'),
            metadata=dict(data.get('metadata') or {}),
        )


@dataclass
class SiteRuntimeCapability:
    name: str
    description: str = ''
    request_schema: Dict[str, Any] = field(default_factory=dict)
    response_schema: Dict[str, Any] = field(default_factory=dict)
    timeout_ms: Optional[int] = None
    requires: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SiteRuntimeCapability':
        return cls(
            name=str(data.get('name', '')),
            description=str(data.get('description', '')),
            request_schema=dict(data.get('request_schema') or {}),
            response_schema=dict(data.get('response_schema') or {}),
            timeout_ms=data.get('timeout_ms'),
            requires=list(data.get('requires') or []),
            metadata=dict(data.get('metadata') or {}),
        )


@dataclass
class SiteRuntimeSite:
    site_name: str
    domains: List[str] = field(default_factory=list)
    test_url: Optional[str] = None
    features: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SiteRuntimeSite':
        return cls(
            site_name=str(data.get('site_name', '')),
            domains=list(data.get('domains') or []),
            test_url=data.get('test_url'),
            features=list(data.get('features') or []),
            metadata=dict(data.get('metadata') or {}),
        )


@dataclass
class SiteRuntimeManifest:
    runtime_id: str
    version: str
    sdk_api_version: str = '2.0'
    display_name: str = ''
    description: str = ''
    capabilities: List[SiteRuntimeCapability] = field(default_factory=list)
    sites: List[SiteRuntimeSite] = field(default_factory=list)
    permissions: List[SiteRuntimePermission] = field(default_factory=list)
    config_schema: Dict[str, Any] = field(default_factory=dict)
    health_policy: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    package_name: Optional[str] = None
    entrypoint: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            'runtime_id': self.runtime_id,
            'version': self.version,
            'sdk_api_version': self.sdk_api_version,
            'display_name': self.display_name,
            'description': self.description,
            'capabilities': [item.to_dict() for item in self.capabilities],
            'sites': [item.to_dict() for item in self.sites],
            'permissions': [item.to_dict() for item in self.permissions],
            'config_schema': dict(self.config_schema),
            'health_policy': dict(self.health_policy),
            'metadata': dict(self.metadata),
            'package_name': self.package_name,
            'entrypoint': self.entrypoint,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SiteRuntimeManifest':
        return cls(
            runtime_id=str(data.get('runtime_id', '')),
            version=str(data.get('version', '')),
            sdk_api_version=str(data.get('sdk_api_version', '2.0')),
            display_name=str(data.get('display_name', '')),
            description=str(data.get('description', '')),
            capabilities=[
                item if isinstance(item, SiteRuntimeCapability) else SiteRuntimeCapability.from_dict(item)
                for item in list(data.get('capabilities') or [])
            ],
            sites=[
                item if isinstance(item, SiteRuntimeSite) else SiteRuntimeSite.from_dict(item)
                for item in list(data.get('sites') or [])
            ],
            permissions=[
                item if isinstance(item, SiteRuntimePermission) else SiteRuntimePermission.from_dict(item)
                for item in list(data.get('permissions') or [])
            ],
            config_schema=dict(data.get('config_schema') or {}),
            health_policy=dict(data.get('health_policy') or {}),
            metadata=dict(data.get('metadata') or {}),
            package_name=data.get('package_name'),
            entrypoint=data.get('entrypoint'),
        )


