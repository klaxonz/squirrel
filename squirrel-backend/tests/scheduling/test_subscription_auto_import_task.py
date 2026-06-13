import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scheduling.base import TaskRegistry
from scheduling.tasks.subscription_auto_import_task import SubscriptionAutoImportTask


def test_subscription_auto_import_task_is_registered_for_scheduler():
    assert SubscriptionAutoImportTask in TaskRegistry.tasks
    assert SubscriptionAutoImportTask.interval == 3
    assert SubscriptionAutoImportTask.unit == "hours"
    assert SubscriptionAutoImportTask.start_immediately is False


def test_subscription_auto_import_task_runs_auto_import_service(monkeypatch):
    calls = []

    monkeypatch.setattr(
        "scheduling.tasks.subscription_auto_import_task.auto_import_missing_subscriptions",
        lambda: calls.append("run") or {
            "users": 2,
            "sites": 3,
            "imported": 5,
            "skipped": 7,
            "failed": 0,
        },
    )

    SubscriptionAutoImportTask.run()

    assert calls == ["run"]
