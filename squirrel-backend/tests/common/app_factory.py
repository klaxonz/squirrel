"""Shared test helpers for building FastAPI test clients.

Route tests construct minimal ``FastAPI`` apps that mount a single router and
override dependencies. Those raw apps miss the production exception handlers
registered in ``application.http.errors.EXCEPTION_HANDLERS`` -- so a
``DomainError`` raised inside a route would surface as an unhandled 500 instead
of its real status. ``create_test_app`` wires those handlers up so tests
exercise the same error-translation path as production.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure the backend root is importable regardless of the test's own sys.path setup.
_BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(_BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(_BACKEND_ROOT))

from fastapi import FastAPI
from fastapi.testclient import TestClient

from application.http.errors import EXCEPTION_HANDLERS


def create_test_app(**kwargs) -> FastAPI:
    """Build a ``FastAPI`` app preconfigured with production handlers."""
    return FastAPI(exception_handlers=EXCEPTION_HANDLERS, **kwargs)


def create_test_client(**kwargs) -> TestClient:
    """Convenience wrapper returning a ``TestClient`` over :func:`create_test_app`."""
    return TestClient(create_test_app(**kwargs))
