"""Protocol definitions for site runtime V2."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, runtime_checkable

from .runtime_models import SiteRuntimeHealthStatus, SiteRuntimeInvokeResponse, SiteRuntimeManifest


@runtime_checkable
class SiteRuntime(Protocol):
    """Contract implemented by each site runtime."""

    def manifest(self) -> SiteRuntimeManifest:
        """Return the static plugin manifest."""
        ...

    def start(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize runtime resources."""
        ...

    def stop(self) -> None:
        """Release runtime resources."""
        ...

    def health(self) -> SiteRuntimeHealthStatus:
        """Return current runtime health."""
        ...

    def invoke(self, capability: str, payload: Optional[Dict[str, Any]] = None) -> SiteRuntimeInvokeResponse:
        """Invoke a named capability."""
        ...


SiteRuntimeFactory = Callable[[], SiteRuntime]
