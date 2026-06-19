from __future__ import annotations

import hashlib
from typing import Any

from ._base import (
    RemoteEntry,
    RemoteFeed,
    RssAccountConfig,
    RssServiceError,
    _JsonHttpClient,
    _parse_datetime,
)


class FeverClient:
    def __init__(self, config: RssAccountConfig, http_client: _JsonHttpClient | None = None) -> None:
        self.config = config
        self.http_client = http_client or _JsonHttpClient()

    def _api_url(self) -> str:
        base_url = self.config.base_url
        if '?' in base_url:
            return base_url if 'api' in base_url else f'{base_url}&api'
        if base_url.endswith('/fever.php') or base_url.endswith('/fever/'):
            return f'{base_url}?api'
        return f'{base_url}/api/fever.php?api'

    def _api_key(self) -> str:
        source = f'{self.config.username or ""}:{self.config.credential}'
        return hashlib.md5(source.encode('utf-8')).hexdigest()

    def _post(self, payload: dict[str, str]) -> dict[str, Any]:
        response = self.http_client.post_json(
            self._api_url(),
            {'api_key': self._api_key(), **payload},
            {
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Squirrel/1.0',
            },
        )
        if not isinstance(response, dict):
            raise RssServiceError('Invalid Fever API response')
        if not response.get('auth'):
            raise RssServiceError('RSS service authentication failed')
        return response

    def list_feeds(self) -> list[RemoteFeed]:
        data = self._post({'feeds': '1'})
        feeds: list[RemoteFeed] = []
        for item in data.get('feeds') or []:
            if not isinstance(item, dict):
                continue
            feed_id = str(item.get('id') or '').strip()
            if not feed_id:
                continue
            feeds.append(
                RemoteFeed(
                    external_feed_id=feed_id,
                    title=str(item.get('title') or item.get('url') or feed_id),
                    feed_url=item.get('url'),
                    site_url=item.get('site_url'),
                    raw_data=dict(item),
                ),
            )
        return feeds

    def list_entries(self, external_feed_id: str, limit: int) -> list[RemoteEntry]:
        data = self._post({'items': '1', 'with_ids': str(external_feed_id)})
        entries: list[RemoteEntry] = []
        for item in data.get('items') or []:
            if not isinstance(item, dict) or str(item.get('feed_id')) != str(external_feed_id):
                continue
            entries.append(_fever_entry_to_remote(item))
            if len(entries) >= limit:
                break
        return entries

    def test_connection(self) -> int:
        return len(self.list_feeds())

    def update_entry(self, external_entry_id: str, is_read: bool | None = None, is_starred: bool | None = None) -> None:
        if is_read is not None:
            self._post(
                {
                    'mark': 'item',
                    'as': 'read' if is_read else 'unread',
                    'id': str(external_entry_id),
                }
            )
        if is_starred is not None:
            self._post(
                {
                    'mark': 'item',
                    'as': 'saved' if is_starred else 'unsaved',
                    'id': str(external_entry_id),
                }
            )

    def subscribe(self, feed_url: str) -> RemoteFeed:
        raise RssServiceError('Fever API does not support subscribing to feeds')

    def unsubscribe(self, external_feed_id: str) -> None:
        raise RssServiceError('Fever API does not support unsubscribing from feeds')


def _fever_entry_to_remote(item: dict[str, Any]) -> RemoteEntry:
    url = str(item.get('url') or '').strip()
    entry_id = str(item.get('id') or url).strip()
    return RemoteEntry(
        external_entry_id=entry_id,
        canonical_url=url or entry_id,
        title=str(item.get('title') or url or entry_id),
        summary=item.get('html'),
        author=item.get('author'),
        published_at=_parse_datetime(item.get('created_on_time')),
        is_read=bool(item.get('is_read')),
        is_starred=bool(item.get('is_saved')),
        raw_data=dict(item),
    )
