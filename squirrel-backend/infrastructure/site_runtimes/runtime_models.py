"""Deprecated: manifest DTOs now live in :mod:`infrastructure.site_runtimes.models`.

This module is retained only as a re-export shim so existing imports
(``from infrastructure.site_runtimes.runtime_models import SiteRuntimeManifest``)
keep working without changes. New code should import from :mod:`models`.
"""
from .models import (
    SiteRuntimeCapability,
    SiteRuntimeManifest,
    SiteRuntimePermission,
    SiteRuntimeSite,
)

__all__ = [
    "SiteRuntimeCapability",
    "SiteRuntimeManifest",
    "SiteRuntimePermission",
    "SiteRuntimeSite",
]
