from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select

from domains.rss.application.services.account.serialization import serialize_entry, serialize_feed
from domains.rss.application.services.client._base import RssServiceError
from domains.rss.domain.models.rss import RssEntry, RssEntryView, RssFeed


class RssLibraryService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    def list_feeds(self, user_id: int, account_id: int | None = None) -> list[dict[str, Any]]:
        with self.session_factory() as session:
            statement = select(RssFeed).where(RssFeed.user_id == user_id)
            if account_id is not None:
                statement = statement.where(RssFeed.account_id == account_id)
            feeds = session.scalars(statement.order_by(RssFeed.title.asc())).all()
            return [serialize_feed(feed) for feed in feeds]

    def update_feed(self, user_id: int, feed_id: int, **kwargs: Any) -> dict[str, Any]:
        allowed_fields = {'category', 'open_method'}
        updates = {key: value for key, value in kwargs.items() if key in allowed_fields}

        if not updates:
            raise RssServiceError('No valid fields to update')

        with self.session_factory() as session:
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
                'total': total,
                'page': page,
                'pageSize': page_size,
                'data': [serialize_entry(entry) for entry in entries],
            }

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
            entry_ids = [view.entry_id for view in views]
            entries = session.scalars(
                select(RssEntry).where(RssEntry.id.in_(entry_ids))
            ).all()
            entry_map = {entry.id: serialize_entry(entry) for entry in entries}
            view_map = {view.entry_id: view.viewed_at for view in views}
            items = []
            for entry_id in entry_ids:
                entry = entry_map.get(entry_id)
                if entry:
                    entry['viewed_at'] = view_map[entry_id].isoformat()
                    items.append(entry)
            return items
