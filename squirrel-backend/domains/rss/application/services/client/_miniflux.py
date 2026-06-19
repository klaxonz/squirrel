from __future__ import annotations

import urllib.parse
from typing import Any

from ._base import (
    RemoteEntry,
    RemoteFeed,
    RssAccountConfig,
    RssServiceError,
    _JsonHttpClient,
    _parse_datetime,
)


class MinifluxClient:
    def __init__(self, config: RssAccountConfig, http_client: _JsonHttpClient | None = None) -> None:
        self.config = config
        self.http_client = http_client or _JsonHttpClient()

    def _headers(self) -> dict[str, str]:
        return {
            'Accept': 'application/json',
            'User-Agent': 'Squirrel/1.0',
            'X-Auth-Token': self.config.credential,
        }

    def list_feeds(self) -> list[RemoteFeed]:
        data = self.http_client.get_json(f'{self.config.base_url}/v1/feeds', self._headers())
        if not isinstance(data, list):
            raise RssServiceError('Invalid Miniflux feeds response')
        feeds: list[RemoteFeed] = []
        for item in data:
            feed_id = str(item.get('id') or item.get('feed_id') or '').strip()
            if not feed_id:
                continue
            category = item.get('category')
            feeds.append(
                RemoteFeed(
                    external_feed_id=feed_id,
                    title=str(item.get('title') or item.get('feed_url') or feed_id),
                    feed_url=item.get('feed_url'),
                    site_url=item.get('site_url'),
                    icon_url=item.get('icon_url'),
                    category=category.get('title') if isinstance(category, dict) else None,
                    raw_data=dict(item),
                ),
            )
        return feeds

    def list_entries(self, external_feed_id: str, limit: int) -> list[RemoteEntry]:
        query = urllib.parse.urlencode({'limit': max(1, limit), 'order': 'published_at', 'direction': 'desc'})
        url = f'{self.config.base_url}/v1/feeds/{urllib.parse.quote(str(external_feed_id))}/entries?{query}'
        data = self.http_client.get_json(url, self._headers())
        entries = data.get('entries') if isinstance(data, dict) else data
        if not isinstance(entries, list):
            raise RssServiceError('Invalid Miniflux entries response')
        return [_miniflux_entry_to_remote(item) for item in entries if isinstance(item, dict)]

    def test_connection(self) -> int:
        return len(self.list_feeds())

    def update_entry(self, external_entry_id: str, is_read: bool | None = None, is_starred: bool | None = None) -> None:
        try:
            eid = int(external_entry_id)
        except ValueError:
            return

        if is_read is not None:
            self.http_client.put_json(
                f'{self.config.base_url}/v1/entries',
                {
                    'entry_ids': [eid],
                    'status': 'read' if is_read else 'unread',
                },
                {**self._headers(), 'Content-Type': 'application/json'},
            )

        if is_starred is not None:
            self.http_client.put_text(
                f'{self.config.base_url}/v1/entries/{eid}/bookmark',
                self._headers(),
            )

    def subscribe(self, feed_url: str, category_id: int | None = None) -> RemoteFeed:
        body: dict[str, Any] = {'feed_url': feed_url}
        if category_id is not None:
            body['category_id'] = category_id
        data = self.http_client.post_json(
            f'{self.config.base_url}/v1/feeds',
            body,
            {**self._headers(), 'Content-Type': 'application/json'},
        )
        if not isinstance(data, dict):
            raise RssServiceError('Invalid Miniflux create feed response')
        feed_id = str(data.get('id') or '').strip()
        if not feed_id:
            raise RssServiceError('Miniflux did not return a feed id')
        category = data.get('category')
        return RemoteFeed(
            external_feed_id=feed_id,
            title=str(data.get('title') or data.get('feed_url') or feed_id),
            feed_url=data.get('feed_url'),
            site_url=data.get('site_url'),
            icon_url=data.get('icon_url'),
            category=category.get('title') if isinstance(category, dict) else None,
            raw_data=dict(data),
        )

    def unsubscribe(self, external_feed_id: str) -> None:
        self.http_client.delete(
            f'{self.config.base_url}/v1/feeds/{urllib.parse.quote(str(external_feed_id))}',
            self._headers(),
        )


def _miniflux_entry_to_remote(item: dict[str, Any]) -> RemoteEntry:
    url = str(item.get('url') or item.get('comments_url') or '').strip()
    entry_id = str(item.get('id') or item.get('hash') or url).strip()
    return RemoteEntry(
        external_entry_id=entry_id,
        canonical_url=url or entry_id,
        title=str(item.get('title') or url or entry_id),
        summary=item.get('content') or item.get('summary'),
        thumbnail=item.get('image_url'),
        author=item.get('author'),
        published_at=_parse_datetime(item.get('published_at') or item.get('created_at')),
        is_read=str(item.get('status') or '').lower() == 'read',
        is_starred=bool(item.get('starred')),
        raw_data=dict(item),
    )
