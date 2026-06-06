from __future__ import annotations

import logging
from dataclasses import replace
from datetime import datetime
from threading import Lock, Thread
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from core.database import get_session
from models.rss import RssAccount, RssEntry, RssEntryView, RssFeed
from services.rss_client_service import (
    RssAccountConfig,
    RssServiceError,
    RemoteEntry,
    RemoteFeed,
    create_client,
)
from services.rss_credential_service import decrypt_credential, encrypt_credential

logger = logging.getLogger(__name__)

_SYNC_LOCK = Lock()
_ACCOUNT_SYNC_LOCKS: dict[int, Lock] = {}
_SYNC_PROGRESS_LOCK = Lock()
_SYNC_PROGRESS: dict[int, dict[str, Any]] = {}

UNSET = object()


def _sync_lock_for_account(account_id: int) -> Lock:
    with _SYNC_LOCK:
        lock = _ACCOUNT_SYNC_LOCKS.get(account_id)
        if lock is None:
            lock = Lock()
            _ACCOUNT_SYNC_LOCKS[account_id] = lock
        return lock


def _set_sync_progress(account_id: int, **values: Any) -> None:
    with _SYNC_PROGRESS_LOCK:
        current = dict(_SYNC_PROGRESS.get(account_id) or {})
        current.update(values)
        current['account_id'] = account_id
        current['updated_at'] = datetime.now().isoformat()
        _SYNC_PROGRESS[account_id] = current


def get_sync_progress(user_id: int, account_id: int) -> Optional[dict[str, Any]]:
    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            return None

    with _SYNC_PROGRESS_LOCK:
        progress = dict(_SYNC_PROGRESS.get(account_id) or {})
    if not progress:
        progress = {
            'account_id': account_id,
            'running': False,
            'phase': 'idle',
            'message': 'RSS sync is idle',
        }
    return progress


def serialize_account(account: RssAccount) -> dict[str, Any]:
    return {
        'id': account.id,
        'provider': account.provider,
        'name': account.name,
        'base_url': account.base_url,
        'username': account.username,
        'enabled': account.enabled,
        'sync_entry_limit': account.sync_entry_limit,
        'last_sync_at': account.last_sync_at.isoformat() if account.last_sync_at else None,
        'last_error': account.last_error,
        'created_at': account.created_at.isoformat() if account.created_at else None,
        'updated_at': account.updated_at.isoformat() if account.updated_at else None,
    }


def serialize_feed(feed: RssFeed) -> dict[str, Any]:
    return {
        'id': feed.id,
        'account_id': feed.account_id,
        'external_feed_id': feed.external_feed_id,
        'title': feed.title,
        'feed_url': feed.feed_url,
        'site_url': feed.site_url,
        'icon_url': feed.icon_url,
        'category': feed.category,
        'enabled': feed.enabled,
        'open_method': feed.open_method,
        'last_entry_sync_at': feed.last_entry_sync_at.isoformat() if feed.last_entry_sync_at else None,
    }


def serialize_entry(entry: RssEntry) -> dict[str, Any]:
    return {
        'id': entry.id,
        'account_id': entry.account_id,
        'feed_id': entry.feed_id,
        'external_entry_id': entry.external_entry_id,
        'canonical_url': entry.canonical_url,
        'title': entry.title,
        'summary': entry.summary,
        'thumbnail': entry.thumbnail,
        'author': entry.author,
        'published_at': entry.published_at.isoformat() if entry.published_at else None,
        'is_read': entry.is_read,
        'is_starred': entry.is_starred,
    }


def _get_account(session: Session, user_id: int, account_id: int) -> Optional[RssAccount]:
    return session.scalars(
        select(RssAccount).where(
            RssAccount.id == account_id,
            RssAccount.user_id == user_id,
            RssAccount.is_deleted.is_(False),
        )
    ).first()


def _config_from_account(account: RssAccount) -> RssAccountConfig:
    return RssAccountConfig(
        provider=account.provider,
        base_url=account.base_url,
        username=account.username,
        credential=decrypt_credential(account.credential_encrypted),
    )


def list_accounts(user_id: int) -> list[dict[str, Any]]:
    with get_session() as session:
        accounts = session.scalars(
            select(RssAccount)
            .where(RssAccount.user_id == user_id, RssAccount.is_deleted.is_(False))
            .order_by(RssAccount.created_at.desc())
        ).all()
        return [serialize_account(account) for account in accounts]


def create_account(
    user_id: int,
    *,
    provider: str,
    name: str,
    base_url: str,
    username: Optional[str],
    credential: str,
    enabled: bool = True,
    sync_entry_limit: Optional[int] = None,
) -> dict[str, Any]:
    from services.rss_client_service import normalize_provider, normalize_base_url, normalize_sync_entry_limit

    provider = normalize_provider(provider)
    base_url = normalize_base_url(base_url)
    sync_entry_limit = normalize_sync_entry_limit(provider, sync_entry_limit)
    name = str(name or '').strip()
    credential = str(credential or '').strip()
    if not name:
        raise RssServiceError('Account name is required')
    if not credential:
        raise RssServiceError('Credential is required')

    with get_session() as session:
        account = RssAccount(
            user_id=user_id,
            provider=provider,
            name=name,
            base_url=base_url,
            username=str(username or '').strip() or None,
            credential_encrypted=encrypt_credential(credential),
            enabled=bool(enabled),
            sync_entry_limit=sync_entry_limit,
            is_deleted=False,
        )
        session.add(account)
        session.commit()
        session.refresh(account)
        return serialize_account(account)


def update_account(
    user_id: int,
    account_id: int,
    *,
    provider: Optional[str] = None,
    name: Optional[str] = None,
    base_url: Optional[str] = None,
    username: Optional[str] = None,
    credential: Optional[str] = None,
    enabled: Optional[bool] = None,
    sync_entry_limit: Any = UNSET,
) -> Optional[dict[str, Any]]:
    from services.rss_client_service import normalize_provider, normalize_base_url, normalize_sync_entry_limit

    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            return None
        if provider is not None:
            account.provider = normalize_provider(provider)
        if sync_entry_limit is not UNSET:
            account.sync_entry_limit = normalize_sync_entry_limit(account.provider, sync_entry_limit)
        elif provider is not None:
            account.sync_entry_limit = normalize_sync_entry_limit(account.provider, account.sync_entry_limit)
        if name is not None:
            normalized_name = str(name or '').strip()
            if not normalized_name:
                raise RssServiceError('Account name is required')
            account.name = normalized_name
        if base_url is not None:
            account.base_url = normalize_base_url(base_url)
        if username is not None:
            account.username = str(username or '').strip() or None
        if credential is not None and str(credential).strip():
            account.credential_encrypted = encrypt_credential(str(credential).strip())
        if enabled is not None:
            account.enabled = bool(enabled)
        session.commit()
        session.refresh(account)
        return serialize_account(account)


def delete_account(user_id: int, account_id: int) -> bool:
    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            return False
        account.is_deleted = True
        account.enabled = False
        session.commit()
        return True


def test_account_config(
    *,
    provider: str,
    base_url: str,
    username: Optional[str],
    credential: str,
) -> dict[str, Any]:
    from services.rss_client_service import normalize_provider, normalize_base_url

    config = RssAccountConfig(
        provider=normalize_provider(provider),
        base_url=normalize_base_url(base_url),
        username=str(username or '').strip() or None,
        credential=str(credential or '').strip(),
    )
    if not config.credential:
        raise RssServiceError('Credential is required')
    feed_count = create_client(config).test_connection()
    return {'ok': True, 'feed_count': feed_count}


def test_account(user_id: int, account_id: int) -> Optional[dict[str, Any]]:
    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            return None
        config = _config_from_account(account)
    feed_count = create_client(config).test_connection()
    return {'ok': True, 'feed_count': feed_count}


def list_feeds(user_id: int, account_id: Optional[int] = None) -> list[dict[str, Any]]:
    with get_session() as session:
        statement = select(RssFeed).where(RssFeed.user_id == user_id)
        if account_id is not None:
            statement = statement.where(RssFeed.account_id == account_id)
        feeds = session.scalars(statement.order_by(RssFeed.title.asc())).all()
        return [serialize_feed(feed) for feed in feeds]


def update_feed(user_id: int, feed_id: int, **kwargs: Any) -> dict[str, Any]:
    allowed_fields = {'category', 'open_method'}
    updates = {k: v for k, v in kwargs.items() if k in allowed_fields}

    if not updates:
        raise RssServiceError('No valid fields to update')

    with get_session() as session:
        feed = session.scalars(
            select(RssFeed).where(
                RssFeed.id == feed_id,
                RssFeed.user_id == user_id,
            )
        ).first()
        if not feed:
            raise RssServiceError('RSS 订阅源不存在')

        for key, value in updates.items():
            setattr(feed, key, value)
        session.commit()
        session.refresh(feed)
        return serialize_feed(feed)


def list_entries(
    user_id: int,
    *,
    account_id: Optional[int] = None,
    feed_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    is_starred: Optional[bool] = None,
    page: int = 1,
    page_size: int = 30,
) -> dict[str, Any]:
    page = max(1, int(page or 1))
    page_size = max(1, min(100, int(page_size or 30)))
    with get_session() as session:
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
            'total': total,
            'page': page,
            'pageSize': page_size,
            'data': [serialize_entry(entry) for entry in entries],
        }


def update_entry(
    user_id: int,
    entry_id: int,
    *,
    is_read: Optional[bool] = None,
    is_starred: Optional[bool] = None,
) -> Optional[dict[str, Any]]:
    with get_session() as session:
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
                    if hasattr(client, 'update_entry'):
                        client.update_entry(ext_eid, is_read=read_val, is_starred=star_val)
                except (OSError, ValueError, TypeError) as e:
                    logger.warning('Failed to sync RSS status to remote in background: %s', e)

            config_data = _config_from_account(account)
            Thread(
                target=_bg_update_remote,
                args=(config_data, entry.external_entry_id, is_read, is_starred),
                daemon=True
            ).start()

        session.commit()
        session.refresh(entry)
        return serialize_entry(entry)


def update_entries_read_status(
    user_id: int,
    entry_ids: list[int],
    *,
    is_read: bool,
) -> dict[str, Any]:
    if not entry_ids:
        return {'updated': 0}

    unique_entry_ids = list(dict.fromkeys(entry_ids))
    remote_targets: list[tuple[RssAccountConfig, str]] = []

    with get_session() as session:
        entries = session.scalars(
            select(RssEntry).where(
                RssEntry.id.in_(unique_entry_ids),
                RssEntry.user_id == user_id,
            )
        ).all()
        changed_entries = [entry for entry in entries if entry.is_read != is_read]

        if not changed_entries:
            return {'updated': 0}

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
        config_by_account_id = {account.id: _config_from_account(account) for account in accounts}

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
                    logger.warning('Failed to sync RSS read status to remote in background: %s', e)

        Thread(target=_bg_update_remote, daemon=True).start()

    return {'updated': len(changed_entries)}


def mark_feed_as_read(user_id: int, feed_id: int) -> dict[str, Any]:
    with get_session() as session:
        statement = select(RssEntry.id).where(
            RssEntry.user_id == user_id,
            RssEntry.feed_id == feed_id,
            RssEntry.is_read.is_(False),
        )
        entry_ids = list(session.scalars(statement).all())

    if not entry_ids:
        return {'updated': 0}

    return update_entries_read_status(user_id, entry_ids, is_read=True)


def record_entry_view(user_id: int, entry_id: int) -> None:
    with get_session() as session:
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


def list_recently_viewed(user_id: int, limit: int = 30) -> list[dict[str, Any]]:
    with get_session() as session:
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
        entry_map = {e.id: serialize_entry(e) for e in entries}
        view_map = {v.entry_id: v.viewed_at for v in views}
        result = []
        for entry_id in entry_ids:
            entry = entry_map.get(entry_id)
            if entry:
                entry['viewed_at'] = view_map[entry_id].isoformat()
                result.append(entry)
        return result