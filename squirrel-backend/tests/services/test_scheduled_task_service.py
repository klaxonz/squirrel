from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from infrastructure.database.base import Base
from infrastructure.scheduling.models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus, TaskType
from infrastructure.scheduling.service import ScheduledTaskService


@pytest.fixture
def svc(session_factory):
    return ScheduledTaskService(session_factory=session_factory)


def test_get_task_list_serializes_only_current_page(engine, svc):
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

    def fake_serialize(task):
        serialized_ids.append(task.id)
        return {'id': task.id, 'name': task.name}

    from unittest.mock import patch

    # get_task_list now serializes each task via serialize_scheduled_task
    # (the SerializerMixin.to_dict() path is gone); patch that instead.
    with patch(
        'infrastructure.scheduling.service.serialize_scheduled_task',
        fake_serialize,
    ):
        result = svc.get_task_list(page=2, page_size=5)

    assert result['total'] == 30
    assert len(result['data']) == 5
    assert serialized_ids == [25, 24, 23, 22, 21]
