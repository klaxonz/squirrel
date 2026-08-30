from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any


class RssSyncProgressStore:
    def __init__(self) -> None:
        self._mutation_locks_guard = Lock()
        self._account_mutation_locks: dict[int, Lock] = {}
        self._progress_lock = Lock()
        self._progress: dict[int, dict[str, Any]] = {}

    def mutation_lock_for_account(self, account_id: int) -> Lock:
        with self._mutation_locks_guard:
            lock = self._account_mutation_locks.get(account_id)
            if lock is None:
                lock = Lock()
                self._account_mutation_locks[account_id] = lock
            return lock

    def lock_for_account(self, account_id: int) -> Lock:
        """Backward-compatible alias for callers that still describe this as a sync lock."""
        return self.mutation_lock_for_account(account_id)

    def set_progress(self, account_id: int, **values: Any) -> None:
        with self._progress_lock:
            current = dict(self._progress.get(account_id) or {})
            current.update(values)
            current['account_id'] = account_id
            current['updated_at'] = datetime.now().isoformat()
            self._progress[account_id] = current

    def get_progress(self, account_id: int) -> dict[str, Any]:
        with self._progress_lock:
            return dict(self._progress.get(account_id) or {})

    def clear_progress(self, account_id: int) -> None:
        with self._progress_lock:
            self._progress.pop(account_id, None)
