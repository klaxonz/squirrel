"""Single-point access to the active :class:`SiteRuntimeManager`.

This module exists as a deliberate, narrow bridge for subsystems that cannot
be reached by explicit dependency injection because they are module-level
singletons consumed from worker processes without any request context —
notably ``SiteCatalog`` (called from the globally-cached
``site_config_manager.get_effective_site_catalog``) and the subscription
``orchestrator`` / ``scheduler`` singletons driven by worker message loops.

Composition roots (:func:`application.lifespan.lifespan` for web,
:func:`workers.bootstrap.bootstrap_runtime` for workers) install the manager
exactly once via :func:`set_runtime_manager`. Everything else reads through
:func:`get_runtime_manager` / :func:`get_runtime_gateway` /
:func:`get_runtime_snapshot`.

Unlike the old ``ports.py`` (which exposed three separate locator functions
that masked who-owns-what), there is exactly one piece of global state here,
and the gateway/snapshot accessors are thin, unambiguous conveniences over
the single manager instance.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .gateway import SiteRuntimeGateway
    from .manager import SiteRuntimeManager
    from .models import SiteRuntimeSnapshot

_runtime_manager: SiteRuntimeManager | None = None


def set_runtime_manager(manager: SiteRuntimeManager) -> None:
    """Install the active runtime manager.

    Called once per process by the composition root. Must be called before any
    code path that reads via :func:`get_runtime_manager`.
    """
    global _runtime_manager
    _runtime_manager = manager


def get_runtime_manager() -> SiteRuntimeManager:
    """Return the active runtime manager.

    Raises ``RuntimeError`` if no manager has been installed — this is
    intentional: callers should fail loudly at first use rather than silently
    fall back to a half-initialized state.
    """
    if _runtime_manager is None:
        raise RuntimeError(
            "SiteRuntimeManager has not been installed. "
            "Call set_runtime_manager() from a composition root first."
        )
    return _runtime_manager


def get_runtime_gateway() -> SiteRuntimeGateway:
    """Convenience: gateway of the active manager."""
    return get_runtime_manager().gateway


def get_runtime_snapshot() -> SiteRuntimeSnapshot:
    """Convenience: fresh snapshot from the active manager."""
    return get_runtime_manager().get_snapshot()


def reset_runtime_manager() -> None:
    """Clear the installed manager (test helper)."""
    global _runtime_manager
    _runtime_manager = None
