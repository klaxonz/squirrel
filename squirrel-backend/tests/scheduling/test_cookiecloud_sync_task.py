import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scheduling.base import TaskRegistry
from scheduling.tasks.cookiecloud_sync_task import CookieCloudSyncTask


def test_cookiecloud_sync_task_is_registered_for_scheduler():
    assert CookieCloudSyncTask in TaskRegistry.tasks
