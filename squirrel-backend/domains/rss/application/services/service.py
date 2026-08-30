from __future__ import annotations

from typing import Any

from domains.rss.application.services.account.serialization import serialize_account, serialize_entry, serialize_feed
from domains.rss.application.services.account.service import RssAccountService
from domains.rss.application.services.sync.service import RssSyncService


class RssService:
    """Application boundary for RSS account, library, and sync workflows."""

    def __init__(
        self,
        session_factory=None,
        *,
        account_service: RssAccountService | None = None,
        sync_service: RssSyncService | None = None,
    ):
        self.account_service = account_service or RssAccountService(session_factory=session_factory)
        self.sync_service = sync_service or RssSyncService(
            session_factory=session_factory,
            account_service=self.account_service,
        )

    def create_account(self, user_id: int, **kwargs: Any) -> dict[str, Any]:
        return self.account_service.create_account(user_id, **kwargs)

    def update_account(self, user_id: int, account_id: int, **kwargs: Any) -> dict[str, Any] | None:
        return self.account_service.update_account(user_id, account_id, **kwargs)

    def delete_account(self, user_id: int, account_id: int) -> bool:
        return self.account_service.delete_account(user_id, account_id)

    def list_accounts(self, user_id: int) -> list[dict[str, Any]]:
        return self.account_service.list_accounts(user_id)

    def test_account(self, user_id: int, account_id: int) -> dict[str, Any] | None:
        return self.account_service.test_account(user_id, account_id)

    def test_account_config(self, **kwargs: Any) -> dict[str, Any]:
        return self.account_service.test_account_config(**kwargs)

    def get_sync_progress(self, user_id: int, account_id: int) -> dict[str, Any] | None:
        return self.account_service.get_sync_progress(user_id, account_id)

    def list_feeds(self, user_id: int, account_id: int | None = None) -> list[dict[str, Any]]:
        return self.account_service.list_feeds(user_id, account_id)

    def update_feed(self, user_id: int, feed_id: int, **kwargs: Any) -> dict[str, Any]:
        return self.account_service.update_feed(user_id, feed_id, **kwargs)

    def list_entries(self, user_id: int, **kwargs: Any) -> dict[str, Any]:
        return self.account_service.list_entries(user_id, **kwargs)

    def get_entry(self, user_id: int, entry_id: int) -> dict[str, Any] | None:
        return self.account_service.get_entry(user_id, entry_id)

    def update_entry(self, user_id: int, entry_id: int, **kwargs: Any) -> dict[str, Any] | None:
        return self.account_service.update_entry(user_id, entry_id, **kwargs)

    def update_entries_read_status(self, user_id: int, entry_ids: list[int], *, is_read: bool) -> dict[str, Any]:
        return self.account_service.update_entries_read_status(user_id, entry_ids, is_read=is_read)

    def mark_feed_as_read(self, user_id: int, feed_id: int) -> dict[str, Any]:
        return self.account_service.mark_feed_as_read(user_id, feed_id)

    def record_entry_view(self, user_id: int, entry_id: int) -> bool:
        return self.account_service.record_entry_view(user_id, entry_id)

    def list_recently_viewed(
        self, user_id: int, limit: int = 30, account_id: int | None = None
    ) -> list[dict[str, Any]]:
        return self.account_service.list_recently_viewed(user_id, limit, account_id)

    def subscribe_feed(self, user_id: int, account_id: int, feed_url: str, category: str | None = None):
        return self.sync_service.subscribe_feed(user_id, account_id, feed_url, category=category)

    def sync_account(
        self, user_id: int, account_id: int, *, entry_limit: int | None = None, force_full_sync: bool = False
    ):
        return self.sync_service.sync_account(
            user_id, account_id, entry_limit=entry_limit, force_full_sync=force_full_sync
        )

    def start_account_sync(
        self, user_id: int, account_id: int, *, entry_limit: int | None = None, force_full_sync: bool = False
    ):
        return self.sync_service.start_account_sync(
            user_id, account_id, entry_limit=entry_limit, force_full_sync=force_full_sync
        )

    def sync_feed(self, user_id: int, feed_id: int, *, entry_limit: int = 50):
        return self.sync_service.sync_feed(user_id, feed_id, entry_limit=entry_limit)

    def unsubscribe_feed(self, user_id: int, account_id: int, feed_id: int) -> bool:
        return self.sync_service.unsubscribe_feed(user_id, account_id, feed_id)

    @staticmethod
    def serialize_account(account):
        return serialize_account(account)

    @staticmethod
    def serialize_entry(entry):
        return serialize_entry(entry)

    @staticmethod
    def serialize_feed(feed):
        return serialize_feed(feed)
