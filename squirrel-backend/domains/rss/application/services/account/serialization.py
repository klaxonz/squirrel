from __future__ import annotations

import re
from html import unescape
from typing import Any

from domains.rss.application.services.client._factory import get_provider_capabilities
from domains.rss.domain.models.rss import RssAccount, RssEntry, RssFeed

_TAG_RE = re.compile(r'<[^>]+>')
_WS_RE = re.compile(r'\s+')
_EXCERPT_MAX_LEN = 280


def entry_excerpt(summary: str | None, *, max_len: int = _EXCERPT_MAX_LEN) -> str | None:
    """Plain-text preview for list rows — never ship full HTML to the entry list."""
    if not summary:
        return None
    text = _WS_RE.sub(' ', _TAG_RE.sub(' ', unescape(summary))).strip()
    if not text:
        return None
    if len(text) <= max_len:
        return text
    return f'{text[: max_len - 1].rstrip()}…'


def serialize_account(account: RssAccount) -> dict[str, Any]:
    return {
        'id': account.id,
        'provider': account.provider,
        'capabilities': get_provider_capabilities(account.provider),
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


def serialize_entry(entry: RssEntry, *, include_summary: bool = True) -> dict[str, Any]:
    payload = {
        'id': entry.id,
        'account_id': entry.account_id,
        'feed_id': entry.feed_id,
        'external_entry_id': entry.external_entry_id,
        'canonical_url': entry.canonical_url,
        'title': entry.title,
        'excerpt': entry_excerpt(entry.summary),
        'thumbnail': entry.thumbnail,
        'author': entry.author,
        'published_at': entry.published_at.isoformat() if entry.published_at else None,
        'is_read': entry.is_read,
        'is_starred': entry.is_starred,
    }
    if include_summary:
        payload['summary'] = entry.summary
    else:
        # List payloads omit full HTML; clients use excerpt for the row preview.
        payload['summary'] = None
    return payload
