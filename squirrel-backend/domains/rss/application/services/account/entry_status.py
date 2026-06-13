from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from domains.rss.domain.models.rss import RssAccount, RssEntry
from domains.rss.application.services.account.remote_status import RssRemoteStatusSyncer
from domains.rss.application.services.account.serialization import serialize_entry

SessionFactory = Callable[[], Generator[Session, None, None]]


class RssEntryStatusService:
    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        config_from_account,
        remote_status_syncer: RssRemoteStatusSyncer,
    ):
        self.session_factory = session_factory
        self.config_from_account = config_from_account
        self.remote_status_syncer = remote_status_syncer

    def update_entry(
        self,
        user_id: int,
        entry_id: int,
        *,
        is_read: bool | None = None,
        is_starred: bool | None = None,
    ) -> dict[str, Any] | None:
        with self.session_factory() as session:
            entry = session.scalars(
                select(RssEntry).where(
                    RssEntry.id == entry_id,
                    RssEntry.user_id == user_id,
                ),
            ).first()
            if not entry:
                return None

            if is_read is not None:
                entry.is_read = is_read
            if is_starred is not None:
                entry.is_starred = is_starred

            account = self._load_enabled_account(session, user_id=user_id, account_id=entry.account_id)
            if account:
                self.remote_status_syncer.update_entry_async(
                    self.config_from_account(account),
                    entry.external_entry_id,
                    is_read=is_read,
                    is_starred=is_starred,
                )

            session.commit()
            session.refresh(entry)
            return serialize_entry(entry)

    def update_entries_read_status(
        self,
        user_id: int,
        entry_ids: list[int],
        *,
        is_read: bool,
    ) -> dict[str, Any]:
        if not entry_ids:
            return {'updated': 0}

        unique_entry_ids = list(dict.fromkeys(entry_ids))
        remote_targets: list[tuple[Any, str]] = []

        with self.session_factory() as session:
            entries = session.scalars(
                select(RssEntry).where(
                    RssEntry.id.in_(unique_entry_ids),
                    RssEntry.user_id == user_id,
                ),
            ).all()
            changed_entries = [entry for entry in entries if entry.is_read != is_read]

            if not changed_entries:
                return {'updated': 0}

            for entry in changed_entries:
                entry.is_read = is_read

            accounts = self._load_enabled_accounts(
                session,
                user_id=user_id,
                account_ids={entry.account_id for entry in changed_entries},
            )
            config_by_account_id = {account.id: self.config_from_account(account) for account in accounts}

            for entry in changed_entries:
                config = config_by_account_id.get(entry.account_id)
                if config:
                    remote_targets.append((config, entry.external_entry_id))

            session.commit()

        self.remote_status_syncer.update_entries_read_status_async(remote_targets, is_read=is_read)

        return {'updated': len(changed_entries)}

    def mark_feed_as_read(self, user_id: int, feed_id: int) -> dict[str, Any]:
        with self.session_factory() as session:
            statement = select(RssEntry.id).where(
                RssEntry.user_id == user_id,
                RssEntry.feed_id == feed_id,
                RssEntry.is_read.is_(False),
            )
            entry_ids = list(session.scalars(statement).all())

        if not entry_ids:
            return {'updated': 0}

        return self.update_entries_read_status(user_id, entry_ids, is_read=True)

    @staticmethod
    def _load_enabled_account(session: Session, *, user_id: int, account_id: int) -> RssAccount | None:
        return session.scalars(
            select(RssAccount).where(
                RssAccount.id == account_id,
                RssAccount.user_id == user_id,
                RssAccount.enabled.is_(True),
                RssAccount.is_deleted.is_(False),
            ),
        ).first()

    @staticmethod
    def _load_enabled_accounts(session: Session, *, user_id: int, account_ids: set[int]) -> list[RssAccount]:
        if not account_ids:
            return []
        return list(
            session.scalars(
                select(RssAccount).where(
                    RssAccount.id.in_(account_ids),
                    RssAccount.user_id == user_id,
                    RssAccount.enabled.is_(True),
                    RssAccount.is_deleted.is_(False),
                ),
            ).all(),
        )
