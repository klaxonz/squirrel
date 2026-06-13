from __future__ import annotations

from datetime import datetime
from threading import Lock
from typing import Any


class RssSyncProgressStore:
    def __init__(self) -> None:
        self._sync_lock = Lock()
        self._account_sync_locks: dict[int, Lock] = {}
        self._progress_lock = Lock()
        self._progress: dict[int, dict[str, Any]] = {}

    def lock_for_account(self, account_id: int) -> Lock:
        with self._sync_lock:
            lock = self._account_sync_locks.get(account_id)
            if lock is None:
                lock = Lock()
                self._account_sync_locks[account_id] = lock
            return lock

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


rss_sync_progress_store = RssSyncProgressStore()
