from __future__ import annotations

import logging
from collections.abc import Iterable
from concurrent.futures import Executor, ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock
from typing import Any

from domains.rss.application.services.client._factory import create_client

logger = logging.getLogger(__name__)

_RemoteEntryKey = tuple[int, str]


@dataclass(frozen=True, slots=True)
class _PendingStatusUpdate:
    config: Any
    is_read: bool | None
    is_starred: bool | None

    def merge(self, newer: _PendingStatusUpdate) -> _PendingStatusUpdate:
        return _PendingStatusUpdate(
            config=newer.config,
            is_read=newer.is_read if newer.is_read is not None else self.is_read,
            is_starred=newer.is_starred if newer.is_starred is not None else self.is_starred,
        )


class RssRemoteStatusSyncer:
    """Serialize remote status writes per account/entry and coalesce queued state.

    A bounded shared executor avoids creating an unbounded daemon thread per UI
    action. While one remote write is running, newer values for that same entry
    replace its queued values so the last local state is always applied last.
    """

    def __init__(self, executor: Executor | None = None) -> None:
        self._executor = executor or ThreadPoolExecutor(max_workers=4, thread_name_prefix='rss-remote-status')
        self._state_lock = Lock()
        self._pending: dict[_RemoteEntryKey, _PendingStatusUpdate] = {}
        self._running: set[_RemoteEntryKey] = set()

    def update_entry_async(
        self,
        account_id: int,
        config: Any,
        external_entry_id: str,
        *,
        is_read: bool | None = None,
        is_starred: bool | None = None,
    ) -> None:
        if is_read is None and is_starred is None:
            return

        key = (account_id, external_entry_id)
        update = _PendingStatusUpdate(config=config, is_read=is_read, is_starred=is_starred)
        should_submit = False
        with self._state_lock:
            pending = self._pending.get(key)
            self._pending[key] = pending.merge(update) if pending else update
            if key not in self._running:
                self._running.add(key)
                should_submit = True

        if not should_submit:
            return

        try:
            self._executor.submit(self._drain_entry, key)
        except Exception:
            with self._state_lock:
                self._pending.pop(key, None)
                self._running.discard(key)
            logger.exception(
                'Failed to submit RSS remote status update: account_id=%s external_entry_id=%s',
                account_id,
                external_entry_id,
            )

    def update_entries_read_status_async(
        self,
        targets: Iterable[tuple[int, Any, str]],
        *,
        is_read: bool,
    ) -> None:
        for account_id, config, external_entry_id in targets:
            self.update_entry_async(
                account_id,
                config,
                external_entry_id,
                is_read=is_read,
            )

    def _drain_entry(self, key: _RemoteEntryKey) -> None:
        while True:
            with self._state_lock:
                update = self._pending.pop(key, None)
                if update is None:
                    self._running.discard(key)
                    return

            try:
                create_client(update.config).update_entry(
                    key[1],
                    is_read=update.is_read,
                    is_starred=update.is_starred,
                )
            except Exception:
                logger.exception(
                    'Failed to sync RSS status to remote: account_id=%s external_entry_id=%s',
                    key[0],
                    key[1],
                )


rss_remote_status_syncer = RssRemoteStatusSyncer()
