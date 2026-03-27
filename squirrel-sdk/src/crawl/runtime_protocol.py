"""Protocol definitions for plugin runtime V2."""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Protocol, runtime_checkable

from .runtime_models import PluginHealthStatus, PluginInvokeResponse, PluginManifest


@runtime_checkable
class PluginRuntime(Protocol):
    """Contract implemented by each plugin runtime."""

    def manifest(self) -> PluginManifest:
        """Return the static plugin manifest."""
        ...

    def start(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize runtime resources."""
        ...

    def stop(self) -> None:
        """Release runtime resources."""
        ...

    def health(self) -> PluginHealthStatus:
        """Return current runtime health."""
        ...

    def invoke(self, capability: str, payload: Optional[Dict[str, Any]] = None) -> PluginInvokeResponse:
        """Invoke a named capability."""
        ...


PluginRuntimeFactory = Callable[[], PluginRuntime]
