"""Records optional startup dependency issues for surfacing via /health.

Previously this was a module-level mutable dict with free functions mutating it
directly — which leaked state across tests and made the registry opaque. The
behaviour is now encapsulated in :class:`StartupIssues`; the module exposes a
process-wide singleton (``_global``) plus thin forwarders so existing call sites
(``record_optional_startup_issue`` etc.) keep working unchanged. Tests that want
isolation can construct their own ``StartupIssues()`` instance.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StartupDependencyIssue:
    name: str
    error: str


class StartupIssues:
    """In-memory registry of optional startup dependency failures."""

    def __init__(self) -> None:
        self._issues: dict[str, StartupDependencyIssue] = {}

    def reset(self) -> None:
        self._issues.clear()

    def record_optional(self, name: str, exc: Exception) -> None:
        self._issues[name] = StartupDependencyIssue(name=name, error=str(exc))

    def clear(self, name: str) -> None:
        self._issues.pop(name, None)

    def list(self) -> list[StartupDependencyIssue]:
        return list(self._issues.values())


# Process-wide singleton; the free functions below forward to it so that
# existing callers (lifespan.py, workers/bootstrap.py, health route) need no
# changes.
_global = StartupIssues()


def reset_startup_dependency_issues() -> None:
    _global.reset()


def record_optional_startup_issue(name: str, exc: Exception) -> None:
    _global.record_optional(name, exc)


def clear_optional_startup_issue(name: str) -> None:
    _global.clear(name)


def list_optional_startup_issues() -> list[StartupDependencyIssue]:
    return _global.list()
