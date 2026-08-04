import os
import sys
from pathlib import Path

import pytest

# Default to dev environment for tests (loads .env.dev with JWT_SECRET_KEY, test DB, etc.)
os.environ.setdefault('ENV', 'dev')

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / 'squirrel-backend'))

from infrastructure.database.base import Base
from shared_kernel.infrastructure import module_discovery

# Match Alembic and application startup: selective SQLite create_all calls still
# need every referenced table registered so SQLAlchemy can resolve model FKs.
module_discovery.import_classes_from_package(package='domains', base_class=Base, recursive=True)

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
