from __future__ import annotations

from dataclasses import replace
from typing import Any

from sqlalchemy import delete, select

from domains.rss.application.services.account.service import RssAccountService
from domains.rss.application.services.client._greader import (
    G_READER_CONTENT_BATCH_SIZE,
    G_READER_QUICK_ENTRIES_PER_FEED,
    G_READER_QUICK_MAX_ENTRIES,
    GReaderClient,
)
from domains.rss.application.services.sync.entry_store import RssEntryStore, rss_entry_store
from domains.rss.domain.models.rss import RssEntry, RssFeed


class GReaderSync:
    def __init__(
        self,
        *,
        session_factory,
        account_service: RssAccountService,
        entry_store: RssEntryStore = rss_entry_store,
    ):
        self.session_factory = session_factory
        self.account_service = account_service
        self.entry_store = entry_store

    def sync_entries(
        self,
        *,
        account_id: int,
        client: GReaderClient,
        feed_refs: list[tuple[int, str, bool]],
        entry_limit: int | None,
        force_full_sync: bool,
    ) -> int:
        synced_entries = self._sync_recent_entries(
            account_id=account_id,
            client=client,
            feed_count=len(feed_refs),
            entry_limit=entry_limit,
            force_full_sync=force_full_sync,
        )

        unread_ids = set(client.fetch_unread_item_ids(limit=200000))
        missing_unread_ids = self._sync_unread_state(account_id=account_id, unread_ids=unread_ids)
        if missing_unread_ids:
            synced_entries += self._import_missing_unread_entries(
                account_id=account_id,
                client=client,
                missing_unread_ids=missing_unread_ids,
                current_synced_entries=synced_entries,
            )

        if force_full_sync:
            self._reconcile_full_reading_state(account_id=account_id, client=client)

        return synced_entries

    def _sync_recent_entries(
        self,
        *,
        account_id: int,
        client: GReaderClient,
        feed_count: int,
        entry_limit: int | None,
        force_full_sync: bool,
    ) -> int:
        greader_entry_limit = entry_limit
        if not force_full_sync:
            quick_entry_limit = min(
                G_READER_QUICK_MAX_ENTRIES,
                max(1, feed_count * G_READER_QUICK_ENTRIES_PER_FEED),
            )
            greader_entry_limit = (
                min(entry_limit, quick_entry_limit)
                if entry_limit is not None
                else quick_entry_limit
            )

        self.account_service.set_sync_progress(
            account_id,
            phase="entries_fetching",
            message="Fetching RSS entries",
            entry_limit=greader_entry_limit,
        )

        def _on_entries_fetched(entry_count: int, continuation: str | None) -> None:
            self.account_service.set_sync_progress(
                account_id,
                phase="entries_fetching",
                entries_fetched=entry_count,
                has_more=bool(continuation),
            )

        synced_entries = 0
        with self.session_factory() as session:
            feeds_by_external_id: dict[str, RssFeed] = {}
            for page in client.iter_recent_entries(greader_entry_limit, _on_entries_fetched):
                new_feeds = self.entry_store.load_feeds_by_external_id(session, account_id, page, feeds_by_external_id)
                feeds_by_external_id.update(new_feeds)
                batch_entries = self.entry_store.upsert_remote_entries_batch(session, feeds_by_external_id, page)
                synced_entries += batch_entries
                self.account_service.set_sync_progress(account_id, phase="entries_saving", entries_synced=synced_entries)
                session.commit()
                if not force_full_sync and batch_entries == 0:
                    break

        return synced_entries

    def _sync_unread_state(self, *, account_id: int, unread_ids: set[str]) -> list[str]:
        with self.session_factory() as session:
            local_rows = session.execute(
                select(RssEntry.id, RssEntry.external_entry_id, RssEntry.is_read)
                .where(RssEntry.account_id == account_id),
            ).all()
            local_by_eid = {
                row.external_entry_id: (row.id, row.is_read)
                for row in local_rows
            }
            missing_unread_ids = list(unread_ids - set(local_by_eid.keys()))
            read_updates = []
            for external_entry_id, (entry_id, is_read) in local_by_eid.items():
                should_read = external_entry_id not in unread_ids
                if is_read != should_read:
                    read_updates.append({"id": entry_id, "is_read": should_read})
            if read_updates:
                session.bulk_update_mappings(RssEntry, read_updates)
                session.commit()
            return missing_unread_ids

    def _import_missing_unread_entries(
        self,
        *,
        account_id: int,
        client: GReaderClient,
        missing_unread_ids: list[str],
        current_synced_entries: int,
    ) -> int:
        self.account_service.set_sync_progress(account_id, phase="entries_fetching", message="Fetching unread RSS entries")

        synced_entries = 0
        with self.session_factory() as session:
            feeds_by_external_id: dict[str, RssFeed] = {}
            for index in range(0, len(missing_unread_ids), G_READER_CONTENT_BATCH_SIZE):
                chunk_ids = missing_unread_ids[index:index + G_READER_CONTENT_BATCH_SIZE]
                page = [
                    replace(entry, is_read=False)
                    for entry in client.fetch_items_contents(chunk_ids)
                ]
                new_feeds = self.entry_store.load_feeds_by_external_id(session, account_id, page, feeds_by_external_id)
                feeds_by_external_id.update(new_feeds)
                batch_entries = self.entry_store.upsert_remote_entries_batch(session, feeds_by_external_id, page)
                synced_entries += batch_entries
                self.account_service.set_sync_progress(
                    account_id,
                    phase="entries_saving",
                    entries_synced=current_synced_entries + synced_entries,
                )
                session.commit()
        return synced_entries

    def _reconcile_full_reading_state(self, *, account_id: int, client: GReaderClient) -> None:
        reading_ids_raw = client.fetch_all_item_ids("reading-list", limit=200000)
        if not reading_ids_raw:
            return

        self.account_service.set_sync_progress(account_id, phase="entries_saving", message="Syncing read/starred state")
        read_ids = set(client.fetch_all_item_ids("user/-/state/com.google/read", limit=200000))
        starred_ids = set(client.fetch_all_item_ids("user/-/state/com.google/starred", limit=50000))
        reading_ids = set(reading_ids_raw)

        with self.session_factory() as session:
            local_rows = session.execute(
                select(RssEntry.id, RssEntry.external_entry_id, RssEntry.is_read, RssEntry.is_starred)
                .where(RssEntry.account_id == account_id),
            ).all()

            local_by_eid: dict[str, tuple[int, bool, bool]] = {
                row.external_entry_id: (row.id, row.is_read, row.is_starred)
                for row in local_rows
            }

            local_ids = set(local_by_eid.keys())
            removed_ids = local_ids - reading_ids

            if removed_ids:
                session.execute(delete(RssEntry).where(
                    RssEntry.account_id == account_id,
                    RssEntry.external_entry_id.in_(list(removed_ids)),
                ))

            update_dicts: list[dict[str, Any]] = []
            for eid, (eid_id, is_read, is_starred) in local_by_eid.items():
                if eid not in reading_ids:
                    continue
                should_read = eid in read_ids
                should_starred = eid in starred_ids
                if is_read != should_read or is_starred != should_starred:
                    update_dicts.append({"id": eid_id, "is_read": should_read, "is_starred": should_starred})

            if update_dicts:
                session.bulk_update_mappings(RssEntry, update_dicts)

            if removed_ids or update_dicts:
                session.commit()
