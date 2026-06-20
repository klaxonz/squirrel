from __future__ import annotations

from threading import Lock

from infrastructure.database.session import get_session
from infrastructure.scheduling.models.scheduled_task import ScheduledTask, TaskExecutionLog
from infrastructure.scheduling.store import dynamic_task_manager


class SchedulerTaskSynchronizer:
    def __init__(self) -> None:
        self._lock = Lock()
        self._fingerprints: dict[int, tuple] = {}

    def seed_task_fingerprints(self) -> None:
        with get_session() as session:
            tasks = session.query(ScheduledTask).all()
            self._fingerprints = {task.id: self._get_task_fingerprint(task) for task in tasks}

    def sync_scheduled_tasks(self) -> None:
        with self._lock, get_session() as session:
            tasks = session.query(ScheduledTask).all()
            current_ids = set()

            for task in tasks:
                current_ids.add(task.id)
                fingerprint = self._get_task_fingerprint(task)
                prev_fingerprint = self._fingerprints.get(task.id)

                if prev_fingerprint is None:
                    if task.is_active:
                        dynamic_task_manager.add_task(task)
                    self._fingerprints[task.id] = fingerprint
                    continue

                if fingerprint != prev_fingerprint:
                    dynamic_task_manager.update_task(task)
                    self._fingerprints[task.id] = fingerprint

            removed_ids = set(self._fingerprints.keys()) - current_ids
            for task_id in removed_ids:
                dynamic_task_manager.remove_task(task_id)
                del self._fingerprints[task_id]

    def consume_manual_triggers(self) -> None:
        pending: list[tuple[int, int, str]] = []
        with get_session() as session:
            logs = (
                session.query(TaskExecutionLog)
                .filter(
                    TaskExecutionLog.status == 'manual_trigger',
                )
                .order_by(TaskExecutionLog.started_at)
                .limit(20)
                .all()
            )

            for log in logs:
                executed_by = log.executed_by or 'manual'
                log.executed_by = executed_by
                log.status = 'queued'
                pending.append((log.task_id, log.id, executed_by))

        for task_id, log_id, executed_by in pending:
            dynamic_task_manager.execute_task_now(task_id, execution_log_id=log_id, executed_by=executed_by)

    @staticmethod
    def _get_task_fingerprint(task: ScheduledTask) -> tuple:
        """Build a hashable fingerprint of the scheduling-relevant task fields.

        Typed access (no getattr) so a wrong type surfaces immediately instead
        of silently producing a different fingerprint.
        """
        return (
            bool(task.is_active),
            int(task.interval),
            str(task.unit),
            bool(task.start_immediately),
        )
