"""Protocol definitions for site runtime V2."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable

from .runtime_models import SiteRuntimeHealthStatus, SiteRuntimeInvokeResponse, SiteRuntimeManifest


@runtime_checkable
class SiteRuntime(Protocol):
    """Contract implemented by each site runtime."""

    def manifest(self) -> SiteRuntimeManifest:
        """Return the static plugin manifest."""
        ...

    def start(self, context: dict[str, Any] | None = None) -> None:
        """Initialize runtime resources."""
        ...

    def stop(self) -> None:
        """Release runtime resources."""
        ...

    def health(self) -> SiteRuntimeHealthStatus:
        """Return current runtime health."""
        ...

    def invoke(self, capability: str, payload: dict[str, Any] | None = None) -> SiteRuntimeInvokeResponse:
        """Invoke a named capability."""
        ...


SiteRuntimeFactory = Callable[[], SiteRuntime]
