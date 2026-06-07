from __future__ import annotations

import logging
from datetime import datetime
from threading import Lock, Thread
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.rss import RssAccount, RssEntry, RssEntryView, RssFeed

logger = logging.getLogger(__name__)

UNSET = object()


class RssAccountService:
    def __init__(self, session_factory=None):
        self.session_factory = session_factory or get_session
        self._sync_lock = Lock()
        self._account_sync_locks: dict[int, Lock] = {}
        self._sync_progress_lock = Lock()
        self._sync_progress: dict[int, dict[str, Any]] = {}

    def _sync_lock_for_account(self, account_id: int) -> Lock:
        with self._sync_lock:
            lock = self._account_sync_locks.get(account_id)
            if lock is None:
                lock = Lock()
                self._account_sync_locks[account_id] = lock
            return lock

    def _set_sync_progress(self, account_id: int, **values: Any) -> None:
        with self._sync_progress_lock:
            current = dict(self._sync_progress.get(account_id) or {})
            current.update(values)
            current["account_id"] = account_id
            current["updated_at"] = datetime.now().isoformat()
            self._sync_progress[account_id] = current

    def get_sync_progress(self, user_id: int, account_id: int) -> dict[str, Any] | None:
        with self.session_factory() as session:
            account = self._get_account(session, user_id, account_id)
            if not account:
                return None

        with self._sync_progress_lock:
            progress = dict(self._sync_progress.get(account_id) or {})
        if not progress:
            progress = {
                "account_id": account_id,
                "running": False,
                "phase": "idle",
                "message": "RSS sync is idle",
            }
        return progress

    @staticmethod
    def serialize_account(account: RssAccount) -> dict[str, Any]:
        return {
            "id": account.id,
            "provider": account.provider,
            "name": account.name,
            "base_url": account.base_url,
            "username": account.username,
            "enabled": account.enabled,
            "sync_entry_limit": account.sync_entry_limit,
            "last_sync_at": account.last_sync_at.isoformat() if account.last_sync_at else None,
            "last_error": account.last_error,
            "created_at": account.created_at.isoformat() if account.created_at else None,
            "updated_at": account.updated_at.isoformat() if account.updated_at else None,
        }

    @staticmethod
    def serialize_feed(feed: RssFeed) -> dict[str, Any]:
        return {
            "id": feed.id,
            "account_id": feed.account_id,
            "external_feed_id": feed.external_feed_id,
            "title": feed.title,
            "feed_url": feed.feed_url,
            "site_url": feed.site_url,
            "icon_url": feed.icon_url,
            "category": feed.category,
            "enabled": feed.enabled,
            "open_method": feed.open_method,
            "last_entry_sync_at": feed.last_entry_sync_at.isoformat() if feed.last_entry_sync_at else None,
        }

    @staticmethod
    def serialize_entry(entry: RssEntry) -> dict[str, Any]:
        return {
            "id": entry.id,
            "account_id": entry.account_id,
            "feed_id": entry.feed_id,
            "external_entry_id": entry.external_entry_id,
            "canonical_url": entry.canonical_url,
            "title": entry.title,
            "summary": entry.summary,
            "thumbnail": entry.thumbnail,
            "author": entry.author,
            "published_at": entry.published_at.isoformat() if entry.published_at else None,
            "is_read": entry.is_read,
            "is_starred": entry.is_starred,
        }

    @staticmethod
    def _get_account(session: Session, user_id: int, account_id: int) -> RssAccount | None:
        return session.scalars(
            select(RssAccount).where(
                RssAccount.id == account_id,
                RssAccount.user_id == user_id,
                RssAccount.is_deleted.is_(False),
            )
        ).first()

    def _config_from_account(self, account: RssAccount) -> Any:
        from services.rss_client_service import RssAccountConfig
        from services.rss_credential_service import decrypt_credential

        return RssAccountConfig(
            provider=account.provider,
            base_url=account.base_url,
            username=account.username,
            credential=decrypt_credential(account.credential_encrypted),
        )

    def list_accounts(self, user_id: int) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            accounts = session.scalars(
                select(RssAccount)
                .where(RssAccount.user_id == user_id, RssAccount.is_deleted.is_(False))
                .order_by(RssAccount.created_at.desc())
            ).all()
            return [self.serialize_account(account) for account in accounts]

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
        from services.rss_client_service import (
            RssServiceError,
            normalize_base_url,
            normalize_provider,
            normalize_sync_entry_limit,
        )
        from services.rss_credential_service import encrypt_credential

        provider = normalize_provider(provider)
        base_url = normalize_base_url(base_url)
        sync_entry_limit = normalize_sync_entry_limit(provider, sync_entry_limit)
        name = str(name or "").strip()
        credential = str(credential or "").strip()
        if not name:
            raise RssServiceError("Account name is required")
        if not credential:
            raise RssServiceError("Credential is required")

        with self.session_factory() as session:
            account = RssAccount(
                user_id=user_id,
                provider=provider,
                name=name,
                base_url=base_url,
                username=str(username or "").strip() or None,
                credential_encrypted=encrypt_credential(credential),
                enabled=bool(enabled),
                sync_entry_limit=sync_entry_limit,
                is_deleted=False,
            )
            session.add(account)
            session.commit()
            session.refresh(account)
            return self.serialize_account(account)

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
        from services.rss_client_service import (
            RssServiceError,
            normalize_base_url,
            normalize_provider,
            normalize_sync_entry_limit,
        )
        from services.rss_credential_service import encrypt_credential

        with self.session_factory() as session:
            account = self._get_account(session, user_id, account_id)
            if not account:
                return None
            if provider is not None:
                account.provider = normalize_provider(provider)
            if sync_entry_limit is not UNSET:
                account.sync_entry_limit = normalize_sync_entry_limit(account.provider, sync_entry_limit)
            elif provider is not None:
                account.sync_entry_limit = normalize_sync_entry_limit(account.provider, account.sync_entry_limit)
            if name is not None:
                normalized_name = str(name or "").strip()
                if not normalized_name:
                    raise RssServiceError("Account name is required")
                account.name = normalized_name
            if base_url is not None:
                account.base_url = normalize_base_url(base_url)
            if username is not None:
                account.username = str(username or "").strip() or None
            if credential is not None and str(credential).strip():
                account.credential_encrypted = encrypt_credential(str(credential).strip())
            if enabled is not None:
                account.enabled = bool(enabled)
            session.commit()
            session.refresh(account)
            return self.serialize_account(account)

    def delete_account(self, user_id: int, account_id: int) -> bool:
        with self.session_factory() as session:
            account = self._get_account(session, user_id, account_id)
            if not account:
                return False
            account.is_deleted = True
            account.enabled = False
            session.commit()
            return True

    @staticmethod
    def test_account_config(
        *,
        provider: str,
        base_url: str,
        username: str | None,
        credential: str,
    ) -> dict[str, Any]:
        from services.rss_client_service import (
            RssAccountConfig,
            RssServiceError,
            create_client,
            normalize_base_url,
            normalize_provider,
        )

        config = RssAccountConfig(
            provider=normalize_provider(provider),
            base_url=normalize_base_url(base_url),
            username=str(username or "").strip() or None,
            credential=str(credential or "").strip(),
        )
        if not config.credential:
            raise RssServiceError("Credential is required")
        feed_count = create_client(config).test_connection()
        return {"ok": True, "feed_count": feed_count}

    def test_account(self, user_id: int, account_id: int) -> dict[str, Any] | None:
        from services.rss_client_service import create_client

        with self.session_factory() as session:
            account = self._get_account(session, user_id, account_id)
            if not account:
                return None
            config = self._config_from_account(account)
        feed_count = create_client(config).test_connection()
        return {"ok": True, "feed_count": feed_count}

    def list_feeds(self, user_id: int, account_id: int | None = None) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement = select(RssFeed).where(RssFeed.user_id == user_id)
            if account_id is not None:
                statement = statement.where(RssFeed.account_id == account_id)
            feeds = session.scalars(statement.order_by(RssFeed.title.asc())).all()
            return [self.serialize_feed(feed) for feed in feeds]

    def update_feed(self, user_id: int, feed_id: int, **kwargs: Any) -> dict[str, Any]:
        from services.rss_client_service import RssServiceError

        allowed_fields = {"category", "open_method"}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

        if not updates:
            raise RssServiceError("No valid fields to update")

        with self.session_factory() as session:
            feed = session.scalars(
                select(RssFeed).where(
                    RssFeed.id == feed_id,
                    RssFeed.user_id == user_id,
                )
            ).first()
            if not feed:
                raise RssServiceError("RSS 订阅源不存在")

            for key, value in updates.items():
                setattr(feed, key, value)
            session.commit()
            session.refresh(feed)
            return self.serialize_feed(feed)

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
        page = max(1, int(page or 1))
        page_size = max(1, min(100, int(page_size or 30)))
        with self.session_factory() as session:
            conditions = [RssEntry.user_id == user_id]
            if account_id is not None:
                conditions.append(RssEntry.account_id == account_id)
            if feed_id is not None:
                conditions.append(RssEntry.feed_id == feed_id)
            if is_read is not None:
                conditions.append(RssEntry.is_read == is_read)
            if is_starred is not None:
                conditions.append(RssEntry.is_starred == is_starred)

            total = session.scalar(select(func.count()).select_from(RssEntry).where(*conditions)) or 0
            entries = session.scalars(
                select(RssEntry)
                .where(*conditions)
                .order_by(RssEntry.published_at.desc().nullslast(), RssEntry.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            ).all()
            return {
                "total": total,
                "page": page,
                "pageSize": page_size,
                "data": [self.serialize_entry(entry) for entry in entries],
            }

    def update_entry(
        self,
        user_id: int,
        entry_id: int,
        *,
        is_read: bool | None = None,
        is_starred: bool | None = None,
    ) -> dict[str, Any] | None:
        from services.rss_client_service import create_client

        with self.session_factory() as session:
            entry = session.scalars(
                select(RssEntry).where(
                    RssEntry.id == entry_id,
                    RssEntry.user_id == user_id,
                )
            ).first()
            if not entry:
                return None

            if is_read is not None:
                entry.is_read = is_read
            if is_starred is not None:
                entry.is_starred = is_starred

            account = session.scalars(
                select(RssAccount).where(
                    RssAccount.id == entry.account_id,
                    RssAccount.user_id == user_id,
                    RssAccount.is_deleted.is_(False),
                )
            ).first()

            if account and account.enabled:
                def _bg_update_remote(config_data, ext_eid, read_val, star_val):
                    try:
                        client = create_client(config_data)
                        if hasattr(client, "update_entry"):
                            client.update_entry(ext_eid, is_read=read_val, is_starred=star_val)
                    except (OSError, ValueError, TypeError) as e:
                        logger.warning("Failed to sync RSS status to remote in background: %s", e)

                config_data = self._config_from_account(account)
                Thread(
                    target=_bg_update_remote,
                    args=(config_data, entry.external_entry_id, is_read, is_starred),
                    daemon=True
                ).start()

            session.commit()
            session.refresh(entry)
            return self.serialize_entry(entry)

    def update_entries_read_status(
        self,
        user_id: int,
        entry_ids: list[int],
        *,
        is_read: bool,
    ) -> dict[str, Any]:
        from services.rss_client_service import create_client

        if not entry_ids:
            return {"updated": 0}

        unique_entry_ids = list(dict.fromkeys(entry_ids))
        remote_targets: list[tuple[Any, str]] = []

        with self.session_factory() as session:
            entries = session.scalars(
                select(RssEntry).where(
                    RssEntry.id.in_(unique_entry_ids),
                    RssEntry.user_id == user_id,
                )
            ).all()
            changed_entries = [entry for entry in entries if entry.is_read != is_read]

            if not changed_entries:
                return {"updated": 0}

            for entry in changed_entries:
                entry.is_read = is_read

            account_ids = {entry.account_id for entry in changed_entries}
            accounts = session.scalars(
                select(RssAccount).where(
                    RssAccount.id.in_(account_ids),
                    RssAccount.user_id == user_id,
                    RssAccount.enabled.is_(True),
                    RssAccount.is_deleted.is_(False),
                )
            ).all()
            config_by_account_id = {account.id: self._config_from_account(account) for account in accounts}

            for entry in changed_entries:
                config = config_by_account_id.get(entry.account_id)
                if config:
                    remote_targets.append((config, entry.external_entry_id))

            session.commit()

        if remote_targets:
            def _bg_update_remote() -> None:
                for config, external_entry_id in remote_targets:
                    try:
                        create_client(config).update_entry(external_entry_id, is_read=is_read)
                    except (OSError, ValueError, TypeError) as e:
                        logger.warning("Failed to sync RSS read status to remote in background: %s", e)

            Thread(target=_bg_update_remote, daemon=True).start()

        return {"updated": len(changed_entries)}

    def mark_feed_as_read(self, user_id: int, feed_id: int) -> dict[str, Any]:
        with self.session_factory() as session:
            statement = select(RssEntry.id).where(
                RssEntry.user_id == user_id,
                RssEntry.feed_id == feed_id,
                RssEntry.is_read.is_(False),
            )
            entry_ids = list(session.scalars(statement).all())

        if not entry_ids:
            return {"updated": 0}

        return self.update_entries_read_status(user_id, entry_ids, is_read=True)

    def record_entry_view(self, user_id: int, entry_id: int) -> None:
        with self.session_factory() as session:
            existing = session.scalars(
                select(RssEntryView).where(
                    RssEntryView.user_id == user_id,
                    RssEntryView.entry_id == entry_id,
                )
            ).first()
            if existing:
                existing.viewed_at = datetime.now()
            else:
                session.add(RssEntryView(
                    user_id=user_id,
                    entry_id=entry_id,
                    viewed_at=datetime.now(),
                ))
            session.commit()

    def list_recently_viewed(self, user_id: int, limit: int = 30) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            views = session.scalars(
                select(RssEntryView)
                .where(RssEntryView.user_id == user_id)
                .order_by(RssEntryView.viewed_at.desc())
                .limit(limit)
            ).all()
            if not views:
                return []
            entry_ids = [v.entry_id for v in views]
            entries = session.scalars(
                select(RssEntry).where(RssEntry.id.in_(entry_ids))
            ).all()
            entry_map = {e.id: self.serialize_entry(e) for e in entries}
            view_map = {v.entry_id: v.viewed_at for v in views}
            result = []
            for entry_id in entry_ids:
                entry = entry_map.get(entry_id)
                if entry:
                    entry["viewed_at"] = view_map[entry_id].isoformat()
                    result.append(entry)
            return result


_default = RssAccountService()
_sync_lock_for_account = _default._sync_lock_for_account
_set_sync_progress = _default._set_sync_progress
get_sync_progress = _default.get_sync_progress
serialize_account = _default.serialize_account
serialize_feed = _default.serialize_feed
serialize_entry = _default.serialize_entry
_get_account = _default._get_account
_config_from_account = _default._config_from_account
list_accounts = _default.list_accounts
create_account = _default.create_account
update_account = _default.update_account
delete_account = _default.delete_account
test_account_config = _default.test_account_config
test_account = _default.test_account
list_feeds = _default.list_feeds
update_feed = _default.update_feed
list_entries = _default.list_entries
update_entry = _default.update_entry
update_entries_read_status = _default.update_entries_read_status
mark_feed_as_read = _default.mark_feed_as_read
record_entry_view = _default.record_entry_view
list_recently_viewed = _default.list_recently_viewed
