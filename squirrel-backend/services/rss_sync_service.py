from __future__ import annotations

import logging
import urllib.parse
from dataclasses import replace
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.rss import RssAccount, RssEntry, RssEntryView, RssFeed
from services.rss_account_service import (
    _config_from_account,
    _get_account,
    _set_sync_progress,
    _sync_lock_for_account,
    serialize_feed,
)
from services.rss_client_service import (
    G_READER_CONTENT_BATCH_SIZE,
    G_READER_QUICK_ENTRIES_PER_FEED,
    G_READER_QUICK_MAX_ENTRIES,
    GReaderClient,
    RemoteEntry,
    RemoteFeed,
    RssServiceError,
    create_client,
)

logger = logging.getLogger(__name__)


def sync_account(user_id: int, account_id: int, *, entry_limit: int | None = None, force_full_sync: bool = False) -> dict[str, Any] | None:
    sync_lock = _sync_lock_for_account(account_id)
    if not sync_lock.acquire(blocking=False):
        raise RssServiceError("RSS account sync is already running")

    _set_sync_progress(
        account_id,
        running=True,
        phase="starting",
        message="Starting RSS sync",
        sync_mode="full" if force_full_sync else "incremental",
        feeds_total=None,
        feeds_synced=0,
        entries_fetched=0,
        entries_synced=0,
        error=None,
        started_at=datetime.now().isoformat(),
        finished_at=None,
    )
    synced_feeds = 0
    synced_entries = 0
    error_message = None
    config = None

    try:
        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if not account:
                return None
            config = _config_from_account(account)
            configured_entry_limit = account.sync_entry_limit

        effective_entry_limit = entry_limit if entry_limit is not None else configured_entry_limit

        client = create_client(config)
        _set_sync_progress(account_id, phase="feeds_fetching", message="Fetching RSS feeds")
        remote_feeds = client.list_feeds()
        _set_sync_progress(
            account_id,
            phase="feeds_saving",
            message="Saving RSS feeds",
            feeds_total=len(remote_feeds),
        )
        feed_refs: list[tuple[int, str, bool]] = []
        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if not account:
                return None
            account.last_error = None
            feeds = _upsert_feeds(session, account, remote_feeds)
            for index, feed in enumerate(feeds, start=1):
                feed_refs.append((feed.id, feed.external_feed_id, feed.enabled))
                if index % 50 == 0 or index == len(feeds):
                    _set_sync_progress(account_id, feeds_synced=index)
        synced_feeds = len(feeds)

        if isinstance(client, GReaderClient):
            greader_entry_limit = effective_entry_limit
            if not force_full_sync:
                quick_entry_limit = min(
                    G_READER_QUICK_MAX_ENTRIES,
                    max(1, len(feed_refs) * G_READER_QUICK_ENTRIES_PER_FEED),
                )
                greader_entry_limit = (
                    min(effective_entry_limit, quick_entry_limit)
                    if effective_entry_limit is not None
                    else quick_entry_limit
                )

            _set_sync_progress(
                account_id,
                phase="entries_fetching",
                message="Fetching RSS entries",
                entry_limit=greader_entry_limit,
            )

            def _on_entries_fetched(entry_count: int, continuation: str | None) -> None:
                _set_sync_progress(
                    account_id,
                    phase="entries_fetching",
                    entries_fetched=entry_count,
                    has_more=bool(continuation),
                )

            with get_session() as session:
                feeds_by_external_id: dict[str, RssFeed] = {}
                for page in client.iter_recent_entries(greader_entry_limit, _on_entries_fetched):
                    new_feeds = _load_feeds_by_external_id(session, account_id, page, feeds_by_external_id)
                    feeds_by_external_id.update(new_feeds)
                    batch_entries = _upsert_remote_entries_batch(session, feeds_by_external_id, page)
                    synced_entries += batch_entries
                    _set_sync_progress(account_id, phase="entries_saving", entries_synced=synced_entries)
                    session.commit()
                    if not force_full_sync and batch_entries == 0:
                        break

            unread_ids = set(client.fetch_unread_item_ids(limit=200000))
            with get_session() as session:
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

            if missing_unread_ids:
                _set_sync_progress(account_id, phase="entries_fetching", message="Fetching unread RSS entries")
                with get_session() as session:
                    feeds_by_external_id: dict[str, RssFeed] = {}
                    for index in range(0, len(missing_unread_ids), G_READER_CONTENT_BATCH_SIZE):
                        chunk_ids = missing_unread_ids[index:index + G_READER_CONTENT_BATCH_SIZE]
                        page = [
                            replace(entry, is_read=False)
                            for entry in client.fetch_items_contents(chunk_ids)
                        ]
                        new_feeds = _load_feeds_by_external_id(session, account_id, page, feeds_by_external_id)
                        feeds_by_external_id.update(new_feeds)
                        batch_entries = _upsert_remote_entries_batch(session, feeds_by_external_id, page)
                        synced_entries += batch_entries
                        _set_sync_progress(account_id, phase="entries_saving", entries_synced=synced_entries)
                        session.commit()

            if force_full_sync:
                reading_ids_raw = client.fetch_all_item_ids("reading-list", limit=200000)
                if reading_ids_raw:
                    _set_sync_progress(account_id, phase="entries_saving", message="Syncing read/starred state")
                    read_ids = set(client.fetch_all_item_ids("user/-/state/com.google/read", limit=200000))
                    starred_ids = set(client.fetch_all_item_ids("user/-/state/com.google/starred", limit=50000))
                    reading_ids = set(reading_ids_raw)

                    with get_session() as session:
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
        else:
            if effective_entry_limit is None:
                raise RssServiceError("Sync entry limit is required for this RSS provider")
            with get_session() as session:
                for feed_id, external_feed_id, enabled in feed_refs:
                    if not enabled:
                        continue
                    _set_sync_progress(
                        account_id,
                        phase="entries_fetching",
                        message="Fetching RSS entries",
                        current_feed_id=feed_id,
                        feeds_synced=synced_feeds,
                    )
                    remote_entries = client.list_entries(external_feed_id, effective_entry_limit)
                    feed = session.scalars(
                        select(RssFeed).where(
                            RssFeed.id == feed_id,
                            RssFeed.user_id == user_id,
                            RssFeed.account_id == account_id,
                        ),
                    ).first()
                    if not feed:
                        continue
                    feeds_by_external_id = {external_feed_id: feed}
                    if remote_entries:
                        remote_entries = [replace(re, external_feed_id=re.external_feed_id or external_feed_id) for re in remote_entries]
                    batch_entries = _upsert_remote_entries_batch(session, feeds_by_external_id, remote_entries)
                    synced_entries += batch_entries
                    feed.last_entry_sync_at = datetime.now()
                    _set_sync_progress(
                        account_id,
                        phase="entries_saving",
                        entries_synced=synced_entries,
                    )
                    session.commit()

        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if account:
                account.last_sync_at = datetime.now()
                account.last_error = None
        _set_sync_progress(
            account_id,
            running=False,
            phase="completed",
            message="RSS sync completed",
            feeds_synced=synced_feeds,
            entries_synced=synced_entries,
            error=None,
            finished_at=datetime.now().isoformat(),
        )
    except Exception as exc:  # sync boundary — catch all to persist error state
        error_message = str(exc)
        provider = config.provider if config else "unknown"
        logger.warning("RSS account sync failed: account_id=%s provider=%s error=%s", account_id, provider, exc)
        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if account:
                account.last_error = error_message
                session.commit()
        _set_sync_progress(
            account_id,
            running=False,
            phase="failed",
            message="RSS sync failed",
            feeds_synced=synced_feeds,
            entries_synced=synced_entries,
            error=error_message,
            finished_at=datetime.now().isoformat(),
        )
        raise
    finally:
        sync_lock.release()

    return {
        "account_id": account_id,
        "feeds": synced_feeds,
        "entries": synced_entries,
        "error": error_message,
    }


def subscribe_feed(
    user_id: int,
    account_id: int,
    feed_url: str,
    category: str | None = None,
) -> dict[str, Any]:
    from services.rss_client_service import RssServiceError

    feed_url = str(feed_url or "").strip()
    if not feed_url:
        raise RssServiceError("Feed URL is required")
    parsed = urllib.parse.urlparse(feed_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise RssServiceError("Feed URL must be an HTTP or HTTPS URL")

    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            raise RssServiceError("RSS account not found")

        config = _config_from_account(account)

        client = create_client(config)
        remote_feed = client.subscribe(feed_url)

        existing = session.scalars(
            select(RssFeed).where(
                RssFeed.account_id == account_id,
                RssFeed.external_feed_id == remote_feed.external_feed_id,
            ),
        ).first()

        if existing:
            existing.title = remote_feed.title or feed_url
            existing.feed_url = remote_feed.feed_url or feed_url
            existing.site_url = remote_feed.site_url
            existing.icon_url = remote_feed.icon_url
            if category is not None:
                existing.category = category
            elif remote_feed.category is not None:
                existing.category = remote_feed.category
            existing.enabled = True
            session.flush()
            feed = existing
        else:
            feed = RssFeed(
                user_id=user_id,
                account_id=account_id,
                external_feed_id=remote_feed.external_feed_id,
                title=remote_feed.title or feed_url,
                feed_url=remote_feed.feed_url or feed_url,
                site_url=remote_feed.site_url,
                icon_url=remote_feed.icon_url,
                category=category or remote_feed.category,
                enabled=True,
                raw_data=remote_feed.raw_data,
            )
            session.add(feed)
            session.flush()

        account.last_error = None
        session.commit()
        session.refresh(feed)
        return serialize_feed(feed)


def sync_feed(user_id: int, feed_id: int, *, entry_limit: int = 50) -> dict[str, Any]:
    with get_session() as session:
        feed = session.scalars(
            select(RssFeed).where(
                RssFeed.id == feed_id,
                RssFeed.user_id == user_id,
            ),
        ).first()
        if not feed:
            raise RssServiceError("RSS 订阅源不存在")

        account = _get_account(session, user_id, feed.account_id)
        if not account or not account.enabled:
            raise RssServiceError("RSS 账号不可用")

        config = _config_from_account(account)
        client = create_client(config)
        external_feed_id = feed.external_feed_id

        remote_entries = client.list_entries(external_feed_id, entry_limit)
        if remote_entries:
            remote_entries = [
                replace(re, external_feed_id=re.external_feed_id or external_feed_id)
                for re in remote_entries
            ]

        feeds_by_external_id = {external_feed_id: feed}
        synced = _upsert_remote_entries_batch(session, feeds_by_external_id, remote_entries)
        feed.last_entry_sync_at = datetime.now()
        feed.enabled = True
        account.last_error = None
        session.commit()

    return {"feed_id": feed_id, "entries": synced}


def unsubscribe_feed(user_id: int, account_id: int, feed_id: int) -> bool:
    from services.rss_client_service import RssServiceError

    with get_session() as session:
        feed = session.scalars(
            select(RssFeed).where(
                RssFeed.id == feed_id,
                RssFeed.account_id == account_id,
                RssFeed.user_id == user_id,
            ),
        ).first()
        if not feed:
            return False

        external_feed_id = feed.external_feed_id

    with get_session() as session:
        account = _get_account(session, user_id, account_id)

    if account and account.enabled:
        try:
            config = _config_from_account(account)
            client = create_client(config)
            client.unsubscribe(external_feed_id)
        except RssServiceError:
            raise
        except (OSError, ValueError, TypeError) as e:
            logger.warning(
                "Failed to sync unsubscribe to remote RSS service: account_id=%s feed_id=%s error=%s",
                account_id, feed_id, e,
            )
            raise RssServiceError(f"Failed to unsubscribe from remote RSS service: {e}") from e

    with get_session() as session:
        feed = session.scalars(
            select(RssFeed).where(
                RssFeed.id == feed_id,
                RssFeed.account_id == account_id,
                RssFeed.user_id == user_id,
            ),
        ).first()
        if not feed:
            return True

        entry_rows = session.execute(
            select(RssEntry.id).where(RssEntry.feed_id == feed_id),
        ).all()
        entry_ids = [row.id for row in entry_rows]
        if entry_ids:
            session.execute(
                delete(RssEntryView).where(RssEntryView.entry_id.in_(entry_ids)),
            )
        session.execute(
            delete(RssEntry).where(RssEntry.feed_id == feed_id),
        )
        session.delete(feed)
        session.commit()

    return True


def _upsert_feeds(session: Session, account: RssAccount, remotes: list[RemoteFeed]) -> list[RssFeed]:
    external_feed_ids = [r.external_feed_id for r in remotes]
    existing_by_id: dict[str, RssFeed] = {}
    if external_feed_ids:
        existing_rows = session.scalars(
            select(RssFeed).where(
                RssFeed.account_id == account.id,
                RssFeed.external_feed_id.in_(external_feed_ids),
            ),
        ).all()
        existing_by_id = {f.external_feed_id: f for f in existing_rows}

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


def _upsert_remote_entries_batch(
    session,
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
        existing = {(e.feed_id, e.external_entry_id): e for e in existing_rows}

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
            if (entry.title == remote_entry.title
                    and entry.summary == remote_entry.summary
                    and entry.author == remote_entry.author
                    and entry.canonical_url == remote_entry.canonical_url
                    and entry.thumbnail == remote_entry.thumbnail
                    and entry.is_read == remote_entry.is_read
                    and entry.is_starred == remote_entry.is_starred
                    and entry.published_at == remote_entry.published_at):
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


def _load_feeds_by_external_id(
    session,
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
