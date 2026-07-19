from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import paginate
from sqlalchemy import or_, select

from domains.rss.application.services.account.serialization import serialize_entry, serialize_feed
from domains.rss.application.services.client._base import RssServiceError
from domains.rss.domain.models.rss import RssAccount, RssEntry, RssEntryView, RssFeed


class RssLibraryService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def list_feeds(self, user_id: int, account_id: int | None = None) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement = (
                select(RssFeed)
                .join(RssAccount, RssAccount.id == RssFeed.account_id)
                .where(
                    RssFeed.user_id == user_id,
                    RssAccount.user_id == user_id,
                    RssAccount.is_deleted.is_(False),
                )
            )
            if account_id is not None:
                statement = statement.where(RssFeed.account_id == account_id)
            feeds = session.scalars(statement.order_by(RssFeed.title.asc())).all()
            return [serialize_feed(feed) for feed in feeds]

    def update_feed(self, user_id: int, feed_id: int, **kwargs: Any) -> dict[str, Any]:
        allowed_fields = {'category', 'open_method'}
        updates = {key: value for key, value in kwargs.items() if key in allowed_fields}

        if not updates:
            raise RssServiceError('No valid fields to update')

        if 'category' in updates:
            category = str(updates['category'] or '').strip() or None
            if category and len(category) > 255:
                raise RssServiceError('RSS category must not exceed 255 characters')
            updates['category'] = category
        if 'open_method' in updates and updates['open_method'] not in {None, 'app_browser', 'external_browser'}:
            raise RssServiceError('Unsupported RSS feed open method')

        with self.session_factory() as session:
            feed = session.scalars(
                select(RssFeed).where(
                    RssFeed.id == feed_id,
                    RssFeed.user_id == user_id,
                    RssFeed.account_id.in_(
                        select(RssAccount.id).where(
                            RssAccount.user_id == user_id,
                            RssAccount.is_deleted.is_(False),
                        )
                    ),
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
        self,
        user_id: int,
        *,
        account_id: int | None = None,
        feed_id: int | None = None,
        is_read: bool | None = None,
        is_starred: bool | None = None,
        query: str | None = None,
        page: int = 1,
        page_size: int = 30,
    ) -> dict[str, Any]:
        with self.session_factory() as session:
            conditions = [
                RssEntry.user_id == user_id,
                RssEntry.account_id.in_(
                    select(RssAccount.id).where(
                        RssAccount.user_id == user_id,
                        RssAccount.is_deleted.is_(False),
                    )
                ),
            ]
            if account_id is not None:
                conditions.append(RssEntry.account_id == account_id)
            if feed_id is not None:
                conditions.append(RssEntry.feed_id == feed_id)
            if is_read is not None:
                conditions.append(RssEntry.is_read == is_read)
            if is_starred is not None:
                conditions.append(RssEntry.is_starred == is_starred)
            search_query = query.strip() if query else ''
            if search_query:
                escaped_query = search_query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                pattern = f'%{escaped_query}%'
                conditions.append(
                    or_(
                        RssEntry.title.ilike(pattern, escape='\\'),
                        RssEntry.summary.ilike(pattern, escape='\\'),
                    )
                )

            entry_page = paginate(
                session,
                select(RssEntry)
                .where(*conditions)
                .order_by(RssEntry.published_at.desc().nullslast(), RssEntry.id.desc()),
                Params(page=page, size=page_size),
            )
            return {
                'total': entry_page.total,
                'page': entry_page.page,
                'pageSize': entry_page.size,
                'data': [serialize_entry(entry) for entry in entry_page.items],
            }

    def record_entry_view(self, user_id: int, entry_id: int) -> bool:
        with self.session_factory() as session:
            entry_exists = session.scalar(
                select(RssEntry.id).where(
                    RssEntry.id == entry_id,
                    RssEntry.user_id == user_id,
                    RssEntry.account_id.in_(
                        select(RssAccount.id).where(
                            RssAccount.user_id == user_id,
                            RssAccount.is_deleted.is_(False),
                        )
                    ),
                )
            )
            if entry_exists is None:
                return False

            existing = session.scalars(
                select(RssEntryView).where(
                    RssEntryView.user_id == user_id,
                    RssEntryView.entry_id == entry_id,
                )
            ).first()
            if existing:
                existing.viewed_at = datetime.now()
            else:
                session.add(
                    RssEntryView(
                        user_id=user_id,
                        entry_id=entry_id,
                        viewed_at=datetime.now(),
                    )
                )
            session.commit()
            return True

    def list_recently_viewed(
        self,
        user_id: int,
        limit: int = 30,
        account_id: int | None = None,
    ) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement = (
                select(RssEntry, RssEntryView.viewed_at)
                .join(RssEntry, RssEntry.id == RssEntryView.entry_id)
                .join(RssAccount, RssAccount.id == RssEntry.account_id)
                .where(
                    RssEntryView.user_id == user_id,
                    RssEntry.user_id == user_id,
                    RssAccount.user_id == user_id,
                    RssAccount.is_deleted.is_(False),
                )
                .order_by(RssEntryView.viewed_at.desc())
                .limit(limit)
            )
            if account_id is not None:
                statement = statement.where(RssEntry.account_id == account_id)
            rows = session.execute(statement).all()
            items: list[dict[str, Any]] = []
            for entry, viewed_at in rows:
                item = serialize_entry(entry)
                item['viewed_at'] = viewed_at.isoformat()
                items.append(item)
            return items
