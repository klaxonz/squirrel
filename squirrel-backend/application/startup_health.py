"""Optional startup step health registry.

A plain in-memory container for failures of *optional* bootstrap steps
(e.g. Cloudflare bypass unavailable), so the web process can surface them via
``/health`` without failing hard. State is carried on
``app.state.startup_health`` (see ``application/lifespan.py``) rather than as a
module-level singleton — that way it is explicit, injectable, and naturally
isolated per test.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StartupHealthIssue:
    name: str
    error: str


class StartupHealth:
    """In-memory registry of optional startup step failures.

    Instantiated once per process and attached to FastAPI's ``app.state`` in
    ``lifespan``; the health route reads it back via
    ``request.app.state.startup_health``.
    """

    def __init__(self) -> None:
        self._issues: dict[str, StartupHealthIssue] = {}

    def record_optional(self, name: str, exc: Exception) -> None:
        self._issues[name] = StartupHealthIssue(name=name, error=str(exc))

    def clear(self, name: str) -> None:
        self._issues.pop(name, None)

    def list(self) -> list[StartupHealthIssue]:
        return list(self._issues.values())
