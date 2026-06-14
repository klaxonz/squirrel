from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.rss.application.services.client._base import RemoteEntry, RemoteFeed
from domains.rss.domain.models.rss import RssAccount, RssEntry, RssFeed


class RssEntryStore:
    @staticmethod
    def upsert_feeds(session: Session, account: RssAccount, remotes: list[RemoteFeed]) -> list[RssFeed]:
        external_feed_ids = [remote.external_feed_id for remote in remotes]
        existing_by_id: dict[str, RssFeed] = {}
        if external_feed_ids:
            existing_rows = session.scalars(
                select(RssFeed).where(
                    RssFeed.account_id == account.id,
                    RssFeed.external_feed_id.in_(external_feed_ids),
                ),
            ).all()
            existing_by_id = {feed.external_feed_id: feed for feed in existing_rows}

        feeds: list[RssFeed] = []
        for remote in remotes:
            feed = existing_by_id.get(remote.external_feed_id)
            if feed is None:
                feed = RssFeed(
                    user_id=account.user_id,
                    account_id=account.id,
                    external_feed_id=remote.external_feed_id,
                    title=remote.title,
                    enabled=True,
                )
                session.add(feed)
                session.flush()

            feed.title = remote.title
            feed.feed_url = remote.feed_url
            feed.site_url = remote.site_url
            feed.icon_url = remote.icon_url
            feed.category = remote.category
            feed.raw_data = remote.raw_data
            feeds.append(feed)

        return feeds

    @staticmethod
    def upsert_remote_entries_batch(
        session: Session,
        feeds_by_external_id: dict[str, RssFeed],
        remote_entries: list[RemoteEntry],
    ) -> int:
        feed_ids: set[int] = set()
        entry_ids: list[str] = []

        for remote_entry in remote_entries:
            if not remote_entry.external_feed_id:
                continue
            feed = feeds_by_external_id.get(remote_entry.external_feed_id)
            if not feed or not feed.enabled:
                continue
            feed_ids.add(feed.id)
            entry_ids.append(remote_entry.external_entry_id)

        existing: dict[tuple[int, str], RssEntry] = {}
        if feed_ids and entry_ids:
            existing_rows = session.scalars(
                select(RssEntry).where(
                    RssEntry.feed_id.in_(feed_ids),
                    RssEntry.external_entry_id.in_(entry_ids),
                ),
            ).all()
            existing = {(entry.feed_id, entry.external_entry_id): entry for entry in existing_rows}

        new_dicts: list[dict[str, Any]] = []
        update_dicts: list[dict[str, Any]] = []
        touched_feeds: set[int] = set()
        now = datetime.now()

        for remote_entry in remote_entries:
            if not remote_entry.external_feed_id:
                continue
            feed = feeds_by_external_id.get(remote_entry.external_feed_id)
            if not feed or not feed.enabled:
                continue
            key = (feed.id, remote_entry.external_entry_id)
            entry = existing.get(key)

            common = dict(
                user_id=feed.user_id,
                account_id=feed.account_id,
                feed_id=feed.id,
                external_entry_id=remote_entry.external_entry_id,
                canonical_url=remote_entry.canonical_url,
                title=remote_entry.title,
                summary=remote_entry.summary,
                thumbnail=remote_entry.thumbnail,
                author=remote_entry.author,
                published_at=remote_entry.published_at,
                is_read=remote_entry.is_read,
                is_starred=remote_entry.is_starred,
                raw_data=remote_entry.raw_data,
            )

            if entry is None:
                common["created_at"] = now
                common["updated_at"] = now
                new_dicts.append(common)
            else:
                if (
                    entry.title == remote_entry.title
                    and entry.summary == remote_entry.summary
                    and entry.author == remote_entry.author
                    and entry.canonical_url == remote_entry.canonical_url
                    and entry.thumbnail == remote_entry.thumbnail
                    and entry.is_read == remote_entry.is_read
                    and entry.is_starred == remote_entry.is_starred
                    and entry.published_at == remote_entry.published_at
                ):
                    continue

                common["id"] = entry.id
                common["updated_at"] = now
                update_dicts.append(common)

            if feed.id not in touched_feeds:
                feed.last_entry_sync_at = now
                touched_feeds.add(feed.id)

        if new_dicts:
            session.bulk_insert_mappings(RssEntry, new_dicts)
        if update_dicts:
            session.bulk_update_mappings(RssEntry, update_dicts)

        return len(new_dicts) + len(update_dicts)

    @staticmethod
    def load_feeds_by_external_id(
        session: Session,
        account_id: int,
        remote_entries: list[RemoteEntry],
        known_feeds: dict[str, RssFeed] | None = None,
    ) -> dict[str, RssFeed]:
        feed_ids = {entry.external_feed_id for entry in remote_entries if entry.external_feed_id}
        if not feed_ids:
            return {}
        if known_feeds:
            feed_ids -= known_feeds.keys()
        if not feed_ids:
            return {}
        feeds = session.scalars(
            select(RssFeed).where(
                RssFeed.account_id == account_id,
                RssFeed.external_feed_id.in_(sorted(feed_ids)),
            ),
        ).all()
        return {feed.external_feed_id: feed for feed in feeds if feed.enabled}


rss_entry_store = RssEntryStore()
