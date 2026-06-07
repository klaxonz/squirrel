from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from models import Base
from models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus, TaskType
from services import scheduled_task_service


@pytest.fixture
def patch_scheduled_task_service(monkeypatch, session_factory):
    monkeypatch.setattr(scheduled_task_service, 'get_session', session_factory)
    monkeypatch.setattr(scheduled_task_service, 'ensure_system_tasks', lambda: None)


def test_get_task_list_serializes_only_current_page(engine, patch_scheduled_task_service):
    Base.metadata.create_all(
        engine,
        tables=[
            ScheduledTask.__table__,
            TaskExecutionLog.__table__,
        ],
    )
    now = datetime(2024, 1, 1)

    with Session(engine, expire_on_commit=False) as session:
        for index in range(30):
            session.add(
                ScheduledTask(
                    name=f'Task {index}',
                    task_type=TaskType.USER.value,
                    description=None,
                    interval=60,
                    unit='seconds',
                    start_immediately=True,
                    max_retries=3,
                    status=TaskStatus.ENABLED.value,
                    is_active=True,
                    task_class='tests.Task',
                    task_params={},
                    created_at=now + timedelta(minutes=index),
                    updated_at=now + timedelta(minutes=index),
                ),
            )
        session.commit()

    serialized_ids = []

    def fake_to_dict(task):
        serialized_ids.append(task.id)
        return {'id': task.id, 'name': task.name}

    from unittest.mock import patch

    with patch.object(ScheduledTask, 'to_dict', fake_to_dict):
        result = scheduled_task_service.ScheduledTaskService.get_task_list(page=2, page_size=5)

    assert result['total'] == 30
    assert len(result['data']) == 5
    assert serialized_ids == [25, 24, 23, 22, 21]
