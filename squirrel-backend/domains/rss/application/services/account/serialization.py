from __future__ import annotations

from typing import Any

from domains.rss.domain.models.rss import RssAccount, RssEntry, RssFeed


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
