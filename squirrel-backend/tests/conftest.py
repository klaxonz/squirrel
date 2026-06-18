import os
import sys
from pathlib import Path

import pytest

# Default to dev environment for tests (loads .env.dev with JWT_SECRET_KEY, test DB, etc.)
os.environ.setdefault('ENV', 'dev')

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'squirrel-site-runtimes' / 'shared'))
sys.path.insert(0, str(REPO_ROOT / 'squirrel-backend'))

pytest_plugins = []


class _FakeRedis:
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, **_kwargs):
        self.values[key] = value
        return True

    def delete(self, key):
        self.values.pop(key, None)
        return True


@pytest.fixture
def mock_redis():
    return _FakeRedis()


@pytest.fixture(autouse=True)
def _isolated_runtime_manager(tmp_path, monkeypatch):
    """Install an isolated SiteRuntimeManager for every test.

    Production code reaches the manager through the single-point
    ``runtime_provider`` (used by deep-stack subsystems like SiteCatalog via
    site_config_manager, and by worker-side singletons). Without an installed
    manager, any code path that resolves the effective site catalog would raise.

    Each test gets a fresh manager backed by a tmp_path store so tests never
    share runtime state or touch the real filesystem.
    """
    from infrastructure.site_runtimes import runtime_provider
    from infrastructure.site_runtimes.manager import SiteRuntimeManager
    from infrastructure.site_runtimes.paths import build_site_runtime_paths

    paths = build_site_runtime_paths(
        repo_root=tmp_path / "repo",
        backend_root=tmp_path / "repo" / "backend",
    )
    manager = SiteRuntimeManager(paths=paths)
    monkeypatch.setattr(runtime_provider, "_runtime_manager", manager)
    yield
    monkeypatch.setattr(runtime_provider, "_runtime_manager", None)
