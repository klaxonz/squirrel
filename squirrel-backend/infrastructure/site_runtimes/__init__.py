"""Site-runtime V2 plugin package for squirrel-backend.

Public symbols are re-exported here for convenience; submodules remain the
authoritative source.
"""
from .models import (
    SiteCapabilityRegistration,
    SiteRuntimeCapability,
    SiteRuntimeDiscoveryError,
    SiteRuntimeDiscoveryResult,
    SiteRuntimeHandle,
    SiteRuntimeHealthSnapshot,
    SiteRuntimeManifest,
    SiteRuntimePermission,
    SiteRuntimeRecord,
    SiteRuntimeSite,
    SiteRuntimeSnapshot,
    SiteRuntimeState,
    SiteRuntimeStatus,
    SiteRuntimeTarget,
    utcnow_iso,
)

__all__ = [
    "SiteCapabilityRegistration",
    "SiteRuntimeCapability",
    "SiteRuntimeDiscoveryError",
    "SiteRuntimeDiscoveryResult",
    "SiteRuntimeHandle",
    "SiteRuntimeHealthSnapshot",
    "SiteRuntimeManifest",
    "SiteRuntimePermission",
    "SiteRuntimeRecord",
    "SiteRuntimeSite",
    "SiteRuntimeSnapshot",
    "SiteRuntimeState",
    "SiteRuntimeStatus",
    "SiteRuntimeTarget",
    "utcnow_iso",
]
