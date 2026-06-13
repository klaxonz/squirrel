from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

import services.rss.account.accounts as accounts
from core.database import get_session
from models.rss import RssAccount
from services.rss.account.accounts import UNSET
from services.rss.account.entry_status import RssEntryStatusService
from services.rss.account.library import RssLibraryService
from services.rss.account.progress import RssSyncProgressStore, rss_sync_progress_store
from services.rss.account.remote_status import RssRemoteStatusSyncer, rss_remote_status_syncer
from services.rss.account.serialization import serialize_feed as _serialize_feed


class RssAccountService:
    def __init__(
        self,
        session_factory=None,
        progress_store: RssSyncProgressStore | None = None,
        remote_status_syncer: RssRemoteStatusSyncer | None = None,
        library_service: RssLibraryService | None = None,
    ):
        self.session_factory = session_factory or get_session
        self.progress_store = progress_store or rss_sync_progress_store
        self.remote_status_syncer = remote_status_syncer or rss_remote_status_syncer
        self.library_service = library_service or RssLibraryService(self.session_factory)
        self.entry_status_service = RssEntryStatusService(
            self.session_factory,
            config_from_account=self.config_from_account,
            remote_status_syncer=self.remote_status_syncer,
        )

    def sync_lock_for_account(self, account_id: int):
        return self.progress_store.lock_for_account(account_id)

    def set_sync_progress(self, account_id: int, **values: Any) -> None:
        self.progress_store.set_progress(account_id, **values)

    def get_sync_progress(self, user_id: int, account_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            account = self.get_account(session, user_id, account_id)
            if not account:
                return None

        progress = self.progress_store.get_progress(account_id)
        if not progress:
            progress = {
                "account_id": account_id,
                "running": False,
                "phase": "idle",
                "message": "RSS sync is idle",
            }
        return progress

    @staticmethod
    def get_account(session: Session, user_id: int, account_id: int) -> RssAccount | None:
        return accounts.get_account(session, user_id, account_id)

    def config_from_account(self, account: RssAccount) -> Any:
        return accounts.config_from_account(account)

    def list_accounts(self, user_id: int) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            return accounts.list_accounts(session, user_id)

    def create_account(
        self,
        user_id: int,
        *,
        provider: str,
        name: str,
        base_url: str,
        username: str | None,
        credential: str,
        enabled: bool = True,
        sync_entry_limit: int | None = None,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            return accounts.create_account(
                session,
                user_id=user_id,
                provider=provider,
                name=name,
                base_url=base_url,
                username=username,
                credential=credential,
                enabled=enabled,
                sync_entry_limit=sync_entry_limit,
            )

    def update_account(
        self,
        user_id: int,
        account_id: int,
        *,
        provider: str | None = None,
        name: str | None = None,
        base_url: str | None = None,
        username: str | None = None,
        credential: str | None = None,
        enabled: bool | None = None,
        sync_entry_limit: Any = UNSET,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            account = self.get_account(session, user_id, account_id)
            if not account:
                return None
            return accounts.update_account(
                session,
                account,
                provider=provider,
                name=name,
                base_url=base_url,
                username=username,
                credential=credential,
                enabled=enabled,
                sync_entry_limit=sync_entry_limit,
            )

    def delete_account(self, user_id: int, account_id: int) -> bool:
        with self.session_factory() as session:
            account = self.get_account(session, user_id, account_id)
            if not account:
                return False
            return accounts.delete_account(session, account)

    @staticmethod
    def test_account_config(
        *,
        provider: str,
        base_url: str,
        username: str | None,
        credential: str,
    ) -> dict[str, Any]:
        return accounts.test_account_config(
            provider=provider,
            base_url=base_url,
            username=username,
            credential=credential,
        )

    def test_account(self, user_id: int, account_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            account = self.get_account(session, user_id, account_id)
            if not account:
                return None
            return accounts.test_account(account)

    def list_feeds(self, user_id: int, account_id: int | None = None) -> list[dict[str, Any]]:
        return self.library_service.list_feeds(user_id, account_id)

    def update_feed(self, user_id: int, feed_id: int, **kwargs: Any) -> dict[str, Any]:
        return self.library_service.update_feed(user_id, feed_id, **kwargs)

    def list_entries(
        self,
        user_id: int,
        *,
        account_id: int | None = None,
        feed_id: int | None = None,
        is_read: bool | None = None,
        is_starred: bool | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> dict[str, Any]:
        return self.library_service.list_entries(
            user_id,
            account_id=account_id,
            feed_id=feed_id,
            is_read=is_read,
            is_starred=is_starred,
            page=page,
            page_size=page_size,
        )

    def update_entry(
        self,
        user_id: int,
        entry_id: int,
        *,
        is_read: bool | None = None,
        is_starred: bool | None = None,
    ) -> dict[str, Any] | None:
        return self.entry_status_service.update_entry(
            user_id,
            entry_id,
            is_read=is_read,
            is_starred=is_starred,
        )

    def update_entries_read_status(
        self,
        user_id: int,
        entry_ids: list[int],
        *,
        is_read: bool,
    ) -> dict[str, Any]:
        return self.entry_status_service.update_entries_read_status(user_id, entry_ids, is_read=is_read)

    def mark_feed_as_read(self, user_id: int, feed_id: int) -> dict[str, Any]:
        return self.entry_status_service.mark_feed_as_read(user_id, feed_id)

    def record_entry_view(self, user_id: int, entry_id: int) -> None:
        self.library_service.record_entry_view(user_id, entry_id)

    def list_recently_viewed(self, user_id: int, limit: int = 30) -> list[dict[str, Any]]:
        return self.library_service.list_recently_viewed(user_id, limit)


rss_account_service = RssAccountService()

serialize_feed = _serialize_feed
sync_lock_for_account = rss_account_service.sync_lock_for_account
set_sync_progress = rss_account_service.set_sync_progress
get_sync_progress = rss_account_service.get_sync_progress
get_account = rss_account_service.get_account
config_from_account = rss_account_service.config_from_account
list_accounts = rss_account_service.list_accounts
create_account = rss_account_service.create_account
update_account = rss_account_service.update_account
delete_account = rss_account_service.delete_account
test_account_config = rss_account_service.test_account_config
test_account = rss_account_service.test_account
list_feeds = rss_account_service.list_feeds
update_feed = rss_account_service.update_feed
list_entries = rss_account_service.list_entries
update_entry = rss_account_service.update_entry
update_entries_read_status = rss_account_service.update_entries_read_status
mark_feed_as_read = rss_account_service.mark_feed_as_read
record_entry_view = rss_account_service.record_entry_view
list_recently_viewed = rss_account_service.list_recently_viewed
