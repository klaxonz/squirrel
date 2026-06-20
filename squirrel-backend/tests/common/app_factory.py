"""Shared test helpers for building FastAPI test clients.

Route tests construct minimal ``FastAPI`` apps that mount a single router and
override dependencies. Those raw apps miss the production exception handlers
registered in ``application.app._EXCEPTION_HANDLERS`` -- so a ``DomainError``
raised inside a route would surface as an unhandled 500 instead of its real
status. ``create_test_app`` wires those handlers up so tests exercise the same
error-translation path as production.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend root is importable regardless of the test's own sys.path setup.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from application.app import _EXCEPTION_HANDLERS  # noqa: E402


def create_test_app(**kwargs) -> FastAPI:
    """Build a ``FastAPI`` app preconfigured with the production exception handlers.

    Extra keyword arguments are forwarded to ``FastAPI()``.
    """
    return FastAPI(exception_handlers=_EXCEPTION_HANDLERS, **kwargs)


def create_test_client(**kwargs) -> TestClient:
    """Convenience wrapper returning a ``TestClient`` over :func:`create_test_app`."""
    return TestClient(create_test_app(**kwargs))
