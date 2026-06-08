import os
import sys
from pathlib import Path

import pytest

# Default to dev environment for tests (loads .env.dev with JWT_SECRET_KEY, test DB, etc.)
os.environ.setdefault('ENV', 'dev')

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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
