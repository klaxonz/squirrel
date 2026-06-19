from __future__ import annotations

import logging
from collections.abc import Iterable
from threading import Thread
from typing import Any

from domains.rss.application.services.client._factory import create_client

logger = logging.getLogger(__name__)


class RssRemoteStatusSyncer:
    @staticmethod
    def update_entry_async(
        config: Any,
        external_entry_id: str,
        *,
        is_read: bool | None = None,
        is_starred: bool | None = None,
    ) -> None:
        def update_remote() -> None:
            try:
                client = create_client(config)
                if hasattr(client, 'update_entry'):
                    client.update_entry(external_entry_id, is_read=is_read, is_starred=is_starred)
            except (OSError, ValueError, TypeError) as exc:
                logger.warning('Failed to sync RSS status to remote in background: %s', exc)

        Thread(target=update_remote, daemon=True).start()

    @staticmethod
    def update_entries_read_status_async(
        targets: Iterable[tuple[Any, str]],
        *,
        is_read: bool,
    ) -> None:
        target_list = list(targets)
        if not target_list:
            return

        def update_remote() -> None:
            for config, external_entry_id in target_list:
                try:
                    create_client(config).update_entry(external_entry_id, is_read=is_read)
                except (OSError, ValueError, TypeError) as exc:
                    logger.warning('Failed to sync RSS read status to remote in background: %s', exc)

        Thread(target=update_remote, daemon=True).start()


rss_remote_status_syncer = RssRemoteStatusSyncer()
