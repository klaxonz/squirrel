from services.rss.account.serialization import serialize_account, serialize_entry
from services.rss.account.service import (
    create_account,
    delete_account,
    get_sync_progress,
    list_accounts,
    list_entries,
    list_feeds,
    list_recently_viewed,
    mark_feed_as_read,
    record_entry_view,
    serialize_feed,
    test_account,
    test_account_config,
    update_account,
    update_entries_read_status,
    update_entry,
    update_feed,
)
from services.rss.sync.service import subscribe_feed, sync_account, sync_feed, unsubscribe_feed


class RssService:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory

    def create_account(
        self,
        user_id,
        *,
        provider,
        name,
        base_url,
        username,
        credential,
        enabled=True,
        sync_entry_limit=None,
    ):
        return create_account(
            user_id,
            provider=provider,
            name=name,
            base_url=base_url,
            username=username,
            credential=credential,
            enabled=enabled,
            sync_entry_limit=sync_entry_limit,
        )

    def delete_account(self, user_id, account_id):
        return delete_account(user_id, account_id)

    def get_sync_progress(self, user_id, account_id):
        return get_sync_progress(user_id, account_id)

    def list_accounts(self, user_id):
        return list_accounts(user_id)

    def list_entries(self, user_id, *, account_id=None, feed_id=None, is_read=None, is_starred=None, page=1, page_size=30):
        return list_entries(
            user_id,
            account_id=account_id,
            feed_id=feed_id,
            is_read=is_read,
            is_starred=is_starred,
            page=page,
            page_size=page_size,
        )

    def list_feeds(self, user_id, account_id=None):
        return list_feeds(user_id, account_id=account_id)

    def list_recently_viewed(self, user_id, limit=30):
        return list_recently_viewed(user_id, limit=limit)

    def mark_feed_as_read(self, user_id, feed_id):
        return mark_feed_as_read(user_id, feed_id)

    def record_entry_view(self, user_id, entry_id):
        return record_entry_view(user_id, entry_id)

    def serialize_account(self, account):
        return serialize_account(account)

    def serialize_entry(self, entry):
        return serialize_entry(entry)

    def serialize_feed(self, feed):
        return serialize_feed(feed)

    def subscribe_feed(self, user_id, account_id, feed_url, category=None):
        return subscribe_feed(user_id, account_id, feed_url, category=category)

    def sync_account(self, user_id, account_id, *, entry_limit=None, force_full_sync=False):
        return sync_account(user_id, account_id, entry_limit=entry_limit, force_full_sync=force_full_sync)

    def sync_feed(self, user_id, feed_id, *, entry_limit=50):
        return sync_feed(user_id, feed_id, entry_limit=entry_limit)

    def test_account(self, user_id, account_id):
        return test_account(user_id, account_id)

    def test_account_config(self, *, provider, base_url, username, credential):
        return test_account_config(provider=provider, base_url=base_url, username=username, credential=credential)

    def unsubscribe_feed(self, user_id, account_id, feed_id):
        return unsubscribe_feed(user_id, account_id, feed_id)

    def update_account(
        self,
        user_id,
        account_id,
        *,
        provider=None,
        name=None,
        base_url=None,
        username=None,
        credential=None,
        enabled=None,
        sync_entry_limit=None,
    ):
        return update_account(
            user_id,
            account_id,
            provider=provider,
            name=name,
            base_url=base_url,
            username=username,
            credential=credential,
            enabled=enabled,
            sync_entry_limit=sync_entry_limit,
        )

    def update_entries_read_status(self, user_id, entry_ids, *, is_read):
        return update_entries_read_status(user_id, entry_ids, is_read=is_read)

    def update_entry(self, user_id, entry_id, *, is_read=None, is_starred=None):
        return update_entry(user_id, entry_id, is_read=is_read, is_starred=is_starred)

    def update_feed(self, user_id, feed_id, **kwargs):
        return update_feed(user_id, feed_id, **kwargs)
