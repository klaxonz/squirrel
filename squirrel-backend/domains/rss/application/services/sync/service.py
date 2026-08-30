from __future__ import annotations

import logging
import urllib.parse
from dataclasses import replace
from datetime import datetime
from threading import Thread
from typing import Any

from sqlalchemy import delete, select

from domains.rss.application.services.account.service import RssAccountService
from domains.rss.application.services.client._base import RssServiceError
from domains.rss.application.services.client._factory import create_client
from domains.rss.application.services.client._greader import GReaderClient
from domains.rss.application.services.sync.entry_store import rss_entry_store
from domains.rss.application.services.sync.greader import GReaderSync
from domains.rss.domain.models.rss import RssEntry, RssEntryView, RssFeed
from infrastructure.database.session import get_session

logger = logging.getLogger(__name__)


class RssSyncService:
    def __init__(
        self,
        session_factory=None,
        account_service: RssAccountService | None = None,
        greader_sync: GReaderSync | None = None,
    ):
        self.session_factory = session_factory or get_session
        self.account_service = account_service or RssAccountService(session_factory=self.session_factory)
        self.greader_sync = greader_sync or GReaderSync(
            session_factory=self.session_factory,
            account_service=self.account_service,
        )

    def sync_account(
        self, user_id: int, account_id: int, *, entry_limit: int | None = None, force_full_sync: bool = False
    ) -> dict[str, Any] | None:
        sync_lock = self._acquire_sync_lock(user_id, account_id)
        if sync_lock is None:
            return None
        self._set_sync_started(account_id, force_full_sync=force_full_sync)
        return self._sync_account_locked(
            user_id,
            account_id,
            sync_lock=sync_lock,
            entry_limit=entry_limit,
            force_full_sync=force_full_sync,
        )

    def start_account_sync(
        self, user_id: int, account_id: int, *, entry_limit: int | None = None, force_full_sync: bool = False
    ) -> dict[str, Any] | None:
        """Atomically reserve an account sync before acknowledging the request."""
        sync_lock = self._acquire_sync_lock(user_id, account_id)
        if sync_lock is None:
            return None
        self._set_sync_started(account_id, force_full_sync=force_full_sync)

        thread = Thread(
            target=self._run_background_sync,
            kwargs={
                'user_id': user_id,
                'account_id': account_id,
                'sync_lock': sync_lock,
                'entry_limit': entry_limit,
                'force_full_sync': force_full_sync,
            },
            name=f'rss-sync-{account_id}',
            daemon=True,
        )
        try:
            thread.start()
        except Exception as exc:
            try:
                self._record_failure(user_id, account_id, 0, 0, str(exc))
            except Exception:
                logger.exception('Failed to record RSS background sync startup failure for account_id=%s', account_id)
            finally:
                sync_lock.release()
            raise
        return {'started': True, 'account_id': account_id}

    def _acquire_sync_lock(self, user_id: int, account_id: int):
        with self.session_factory() as session:
            if not self.account_service.get_account(session, user_id, account_id):
                return None

        sync_lock = self.account_service.sync_lock_for_account(account_id)
        if not sync_lock.acquire(blocking=False):
            raise RssServiceError('RSS account sync is already running')

        with self.session_factory() as session:
            if not self.account_service.get_account(session, user_id, account_id):
                sync_lock.release()
                return None
        return sync_lock

    def _set_sync_started(self, account_id: int, *, force_full_sync: bool) -> None:
        self.account_service.set_sync_progress(
            account_id,
            running=True,
            phase='starting',
            message='Starting RSS sync',
            sync_mode='full' if force_full_sync else 'incremental',
            feeds_total=None,
            feeds_synced=0,
            entries_fetched=0,
            entries_synced=0,
            error=None,
            started_at=datetime.now().isoformat(),
            finished_at=None,
        )

    def _run_background_sync(self, **kwargs: Any) -> None:
        account_id = kwargs['account_id']
        try:
            self._sync_account_locked(**kwargs)
        except Exception:
            logger.exception('Background RSS sync failed for account_id=%s', account_id)

    def _sync_account_locked(
        self,
        user_id: int,
        account_id: int,
        *,
        sync_lock,
        entry_limit: int | None,
        force_full_sync: bool,
    ) -> dict[str, Any] | None:
        synced_feeds = 0
        synced_entries = 0
        error_message = None
        config = None

        try:
            loaded = self._load_account_and_config(user_id, account_id)
            if loaded is None:
                self.account_service.progress_store.clear_progress(account_id)
                return None
            _account, config, configured_entry_limit = loaded
            effective_entry_limit = entry_limit if entry_limit is not None else configured_entry_limit

            client = create_client(config)
            synced_feeds, feed_refs = self._sync_feeds(user_id, account_id, client)
            synced_entries = self._sync_entries(
                user_id,
                account_id,
                client,
                feed_refs,
                feeds_synced=synced_feeds,
                entry_limit=effective_entry_limit,
                force_full_sync=force_full_sync,
            )
            self._finalize_success(user_id, account_id, synced_feeds, synced_entries)
        except Exception as exc:
            error_message = str(exc)
            provider = config.provider if config else 'unknown'
            logger.warning('RSS account sync failed: account_id=%s provider=%s error=%s', account_id, provider, exc)
            self._record_failure(user_id, account_id, synced_feeds, synced_entries, error_message)
            raise
        finally:
            sync_lock.release()

        return {
            'account_id': account_id,
            'feeds': synced_feeds,
            'entries': synced_entries,
            'error': error_message,
        }

    def _load_account_and_config(self, user_id: int, account_id: int):
        """Load the account and derive its config + configured entry limit.

        Returns ``(account, config, sync_entry_limit)`` or ``None`` if the account is gone.
        """
        with self.session_factory() as session:
            account = self.account_service.get_account(session, user_id, account_id)
            if not account:
                return None
            config = self.account_service.config_from_account(account)
            configured_entry_limit = account.sync_entry_limit
        return account, config, configured_entry_limit

    def _sync_feeds(self, user_id: int, account_id: int, client) -> tuple[int, list[tuple[int, str, bool]]]:
        """Fetch remote feeds, persist them, and report progress. Returns ``(feed_count, feed_refs)``."""
        self.account_service.set_sync_progress(account_id, phase='feeds_fetching', message='Fetching RSS feeds')
        remote_feeds = client.list_feeds()
        self.account_service.set_sync_progress(
            account_id,
            phase='feeds_saving',
            message='Saving RSS feeds',
            feeds_total=len(remote_feeds),
        )
        feed_refs: list[tuple[int, str, bool]] = []
        with self.session_factory() as session:
            account = self.account_service.get_account(session, user_id, account_id)
            if not account:
                return 0, feed_refs
            account.last_error = None
            feeds = rss_entry_store.upsert_feeds(session, account, remote_feeds)
            for index, feed in enumerate(feeds, start=1):
                feed_refs.append((feed.id, feed.external_feed_id, feed.enabled))
                if index % 50 == 0 or index == len(feeds):
                    self.account_service.set_sync_progress(account_id, feeds_synced=index)
        return len(feeds), feed_refs

    def _sync_entries(
        self,
        user_id: int,
        account_id: int,
        client,
        feed_refs: list[tuple[int, str, bool]],
        *,
        feeds_synced: int,
        entry_limit: int | None,
        force_full_sync: bool,
    ) -> int:
        """Sync entries for the given feeds. GReader accounts delegate to ``greader_sync``;
        other providers use a per-feed fetch/upsert loop. Returns the entry count synced.
        """
        if isinstance(client, GReaderClient):
            return self.greader_sync.sync_entries(
                account_id=account_id,
                client=client,
                feed_refs=feed_refs,
                entry_limit=entry_limit,
                force_full_sync=force_full_sync,
            )

        if entry_limit is None:
            raise RssServiceError('Sync entry limit is required for this RSS provider')

        synced_entries = 0
        with self.session_factory() as session:
            for feed_id, external_feed_id, enabled in feed_refs:
                if not enabled:
                    continue
                self.account_service.set_sync_progress(
                    account_id,
                    phase='entries_fetching',
                    message='Fetching RSS entries',
                    current_feed_id=feed_id,
                    feeds_synced=feeds_synced,
                )
                remote_entries = client.list_entries(external_feed_id, entry_limit)
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
                    remote_entries = [
                        replace(re, external_feed_id=re.external_feed_id or external_feed_id) for re in remote_entries
                    ]
                batch_entries = rss_entry_store.upsert_remote_entries_batch(
                    session, feeds_by_external_id, remote_entries
                )
                synced_entries += batch_entries
                feed.last_entry_sync_at = datetime.now()
                self.account_service.set_sync_progress(
                    account_id,
                    phase='entries_saving',
                    entries_synced=synced_entries,
                )
                session.commit()
        return synced_entries

    def _finalize_success(self, user_id: int, account_id: int, feeds: int, entries: int) -> None:
        """Stamp ``last_sync_at`` and report the completed progress."""
        with self.session_factory() as session:
            account = self.account_service.get_account(session, user_id, account_id)
            if account:
                account.last_sync_at = datetime.now()
                account.last_error = None
        self.account_service.set_sync_progress(
            account_id,
            running=False,
            phase='completed',
            message='RSS sync completed',
            feeds_synced=feeds,
            entries_synced=entries,
            error=None,
            finished_at=datetime.now().isoformat(),
        )

    def _record_failure(self, user_id: int, account_id: int, feeds: int, entries: int, error_message: str) -> None:
        """Persist ``last_error`` and report the failed progress."""
        with self.session_factory() as session:
            account = self.account_service.get_account(session, user_id, account_id)
            if account:
                account.last_error = error_message
                session.commit()
        self.account_service.set_sync_progress(
            account_id,
            running=False,
            phase='failed',
            message='RSS sync failed',
            feeds_synced=feeds,
            entries_synced=entries,
            error=error_message,
            finished_at=datetime.now().isoformat(),
        )

    def subscribe_feed(
        self,
        user_id: int,
        account_id: int,
        feed_url: str,
        category: str | None = None,
    ) -> dict[str, Any]:
        feed_url = str(feed_url or '').strip()
        if not feed_url:
            raise RssServiceError('Feed URL is required')
        parsed = urllib.parse.urlparse(feed_url)
        if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
            raise RssServiceError('Feed URL must be an HTTP or HTTPS URL')

        with self.session_factory() as session:
            if not self.account_service.get_account(session, user_id, account_id):
                raise RssServiceError('RSS account not found')

        with self.account_service.account_mutation(
            account_id,
            conflict_message='Cannot subscribe while the RSS account is syncing or being modified',
        ):
            with self.session_factory() as session:
                account = self.account_service.get_account(session, user_id, account_id)
                if not account:
                    raise RssServiceError('RSS account not found')
                config = self.account_service.config_from_account(account)

            client = create_client(config)
            remote_feed = client.subscribe(feed_url)

            with self.session_factory() as session:
                account = self.account_service.get_account(session, user_id, account_id)
                if not account:
                    raise RssServiceError('RSS account not found')

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
                return self.account_service.serialize_feed(feed)

    def sync_feed(self, user_id: int, feed_id: int, *, entry_limit: int = 50) -> dict[str, Any]:
        with self.session_factory() as session:
            account_id = session.scalar(
                select(RssFeed.account_id).where(
                    RssFeed.id == feed_id,
                    RssFeed.user_id == user_id,
                )
            )
        if account_id is None:
            raise RssServiceError('RSS 订阅源不存在')

        with self.account_service.account_mutation(
            account_id,
            conflict_message='Cannot sync a feed while its RSS account is syncing or being modified',
        ):
            with self.session_factory() as session:
                feed = session.scalars(
                    select(RssFeed).where(
                        RssFeed.id == feed_id,
                        RssFeed.user_id == user_id,
                        RssFeed.account_id == account_id,
                    ),
                ).first()
                if not feed:
                    raise RssServiceError('RSS 订阅源不存在')

                account = self.account_service.get_account(session, user_id, account_id)
                if not account or not account.enabled:
                    raise RssServiceError('RSS 账号不可用')

                config = self.account_service.config_from_account(account)
                external_feed_id = feed.external_feed_id

            client = create_client(config)
            remote_entries = client.list_entries(external_feed_id, entry_limit)
            if remote_entries:
                remote_entries = [
                    replace(re, external_feed_id=re.external_feed_id or external_feed_id) for re in remote_entries
                ]

            with self.session_factory() as session:
                feed = session.scalars(
                    select(RssFeed).where(
                        RssFeed.id == feed_id,
                        RssFeed.user_id == user_id,
                        RssFeed.account_id == account_id,
                    ),
                ).first()
                account = self.account_service.get_account(session, user_id, account_id)
                if not feed or not account or not account.enabled:
                    raise RssServiceError('RSS 订阅源或账号不可用')

                feeds_by_external_id = {external_feed_id: feed}
                synced = rss_entry_store.upsert_remote_entries_batch(session, feeds_by_external_id, remote_entries)
                feed.last_entry_sync_at = datetime.now()
                feed.enabled = True
                account.last_error = None
                session.commit()

        return {'feed_id': feed_id, 'entries': synced}

    def unsubscribe_feed(self, user_id: int, account_id: int, feed_id: int) -> bool:
        with self.session_factory() as session:
            feed_exists = session.scalar(
                select(RssFeed.id).where(
                    RssFeed.id == feed_id,
                    RssFeed.account_id == account_id,
                    RssFeed.user_id == user_id,
                )
            )
            if feed_exists is None:
                return False

        with self.account_service.account_mutation(
            account_id,
            conflict_message='Cannot unsubscribe while the RSS account is syncing or being modified',
        ):
            with self.session_factory() as session:
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
                account = self.account_service.get_account(session, user_id, account_id)
                config = self.account_service.config_from_account(account) if account and account.enabled else None

            if config:
                try:
                    create_client(config).unsubscribe(external_feed_id)
                except RssServiceError:
                    raise
                except (OSError, ValueError, TypeError) as e:
                    logger.warning(
                        'Failed to sync unsubscribe to remote RSS service: account_id=%s feed_id=%s error=%s',
                        account_id,
                        feed_id,
                        e,
                    )
                    raise RssServiceError(f'Failed to unsubscribe from remote RSS service: {e}') from e

            with self.session_factory() as session:
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
