from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from models import Base
from models.scheduled_task import ScheduledTask, TaskExecutionLog, TaskStatus, TaskType
from services import scheduled_task_service


@contextmanager
def _managed_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def _setup_test_env(monkeypatch):
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(
        engine,
        tables=[
            ScheduledTask.__table__,
            TaskExecutionLog.__table__,
        ],
    )
    monkeypatch.setattr(scheduled_task_service, 'get_session', lambda: _managed_session(engine))
    monkeypatch.setattr(scheduled_task_service, 'ensure_system_tasks', lambda: None)
    return engine


def test_get_task_list_serializes_only_current_page(monkeypatch):
    engine = _setup_test_env(monkeypatch)
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
                )
            )
        session.commit()

    serialized_ids = []

    def fake_to_dict(task):
        serialized_ids.append(task.id)
        return {'id': task.id, 'name': task.name}

    monkeypatch.setattr(ScheduledTask, 'to_dict', fake_to_dict)

    result = scheduled_task_service.ScheduledTaskService.get_task_list(page=2, page_size=5)

    assert result['total'] == 30
    assert len(result['data']) == 5
    assert serialized_ids == [25, 24, 23, 22, 21]
