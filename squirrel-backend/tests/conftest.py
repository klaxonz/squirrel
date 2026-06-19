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
