from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from infrastructure.database.base import Base
from infrastructure.scheduling.base import BaseTask
from infrastructure.scheduling.bootstrap import ScheduledTaskBootstrap
from infrastructure.scheduling.factory import TaskFactory
from infrastructure.scheduling.models.scheduled_task import ScheduledTask, TaskStatus, TaskType


@contextmanager
def _get_session(engine):
    session = Session(engine, expire_on_commit=False)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def test_ensure_system_tasks_updates_existing_system_task_class_by_name():
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine, tables=[ScheduledTask.__table__])

    class SubscriptionPendingReconcileTask(BaseTask):
        pass

    SubscriptionPendingReconcileTask.__module__ = 'workers.scheduling.tasks.subscription_pending_reconcile_task'

    with Session(engine, expire_on_commit=False) as session:
        session.add(
            ScheduledTask(
                name='SubscriptionPendingReconcileTask',
                task_type=TaskType.SYSTEM.value,
                description=None,
                interval=60,
                unit='seconds',
                start_immediately=True,
                max_retries=3,
                status=TaskStatus.ERROR.value,
                is_active=True,
                task_class='schedule.tasks.subscription_pending_reconcile_task.SubscriptionPendingReconcileTask',
                task_params={},
                last_error='Cannot create task instance for SubscriptionPendingReconcileTask',
                created_by='system',
                updated_by='system',
            ),
        )
        session.commit()

    bootstrap = ScheduledTaskBootstrap(session_factory=lambda: _get_session(engine))
    bootstrap.ensure_system_tasks([SubscriptionPendingReconcileTask])

    with Session(engine, expire_on_commit=False) as session:
        tasks = session.query(ScheduledTask).all()

    assert len(tasks) == 1
    assert tasks[0].task_class == (
        'workers.scheduling.tasks.subscription_pending_reconcile_task.SubscriptionPendingReconcileTask'
    )
    assert tasks[0].status == TaskStatus.ENABLED.value
    assert tasks[0].last_error is None


def test_task_factory_discovers_nested_worker_task_modules():
    factory = TaskFactory()

    factory.discover_builtin_tasks()

    assert factory.get_task_class(
        'workers.scheduling.tasks.subscription_pending_reconcile_task.SubscriptionPendingReconcileTask',
    ) is not None
    assert factory.get_task_class('infrastructure.scheduling.base.BaseTask') is None
