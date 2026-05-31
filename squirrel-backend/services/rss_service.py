from __future__ import annotations

import base64
import hashlib
import json
import logging
from threading import Lock, Thread
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Callable, Iterator, Optional

from cryptography.fernet import Fernet
from sqlalchemy import delete, func, select

from core.config import settings
from core.database import get_session
from models.rss import RssAccount, RssEntry, RssEntryView, RssFeed

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {'greader', 'miniflux', 'fever'}
G_READER_PAGE_SIZE = 1000
G_READER_CONTENT_BATCH_SIZE = 500
G_READER_QUICK_ENTRIES_PER_FEED = 10
G_READER_QUICK_MAX_ENTRIES = 1000
G_READER_READ_STATE = 'user/-/state/com.google/read'
G_READER_STARRED_STATE = 'user/-/state/com.google/starred'
UNSET = object()
_SYNC_LOCK = Lock()
_ACCOUNT_SYNC_LOCKS: dict[int, Lock] = {}
_SYNC_PROGRESS_LOCK = Lock()
_SYNC_PROGRESS: dict[int, dict[str, Any]] = {}


class RssServiceError(ValueError):
    pass


@dataclass
class RssAccountConfig:
    provider: str
    base_url: str
    username: Optional[str]
    credential: str


@dataclass
class RemoteFeed:
    external_feed_id: str
    title: str
    feed_url: Optional[str] = None
    site_url: Optional[str] = None
    icon_url: Optional[str] = None
    category: Optional[str] = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteEntry:
    external_entry_id: str
    canonical_url: str
    title: str
    external_feed_id: Optional[str] = None
    summary: Optional[str] = None
    thumbnail: Optional[str] = None
    author: Optional[str] = None
    published_at: Optional[datetime] = None
    is_read: bool = False
    is_starred: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)


def _fernet() -> Fernet:
    digest = hashlib.sha256(settings.JWT_SECRET_KEY.encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def _encrypt(value: str) -> str:
    return _fernet().encrypt(value.encode('utf-8')).decode('utf-8')


def _decrypt(value: str) -> str:
    return _fernet().decrypt(value.encode('utf-8')).decode('utf-8')


def _normalize_provider(provider: str) -> str:
    normalized = str(provider or '').strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise RssServiceError(f'Unsupported RSS provider: {provider}')
    return normalized


def _normalize_base_url(base_url: str) -> str:
    normalized = str(base_url or '').strip().rstrip('/')
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise RssServiceError('RSS service URL must be an HTTP or HTTPS URL')
    return normalized


def _normalize_sync_entry_limit(provider: str, sync_entry_limit: Optional[int]) -> Optional[int]:
    if sync_entry_limit is None:
        if provider == 'greader':
            return None
        raise RssServiceError('Sync entry limit is required for this RSS provider')
    limit = int(sync_entry_limit)
    if limit < 1:
        raise RssServiceError('Sync entry limit must be greater than 0')
    return limit


def _parse_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        timestamp = float(value)
        if timestamp > 10_000_000_000:
            timestamp = timestamp / 1000
        return datetime.fromtimestamp(timestamp)
    text = str(value).strip()
    if not text:
        return None
    if text.endswith('Z'):
        text = f'{text[:-1]}+00:00'
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


class _JsonHttpClient:
    def get_json(self, url: str, headers: dict[str, str]) -> Any:
        request = urllib.request.Request(url, headers=headers, method='GET')
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))

    def post_text(self, url: str, data: dict[str, str], headers: dict[str, str]) -> str:
        body = urllib.parse.urlencode(data).encode('utf-8')
        request = urllib.request.Request(url, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode('utf-8')

    def post_json(self, url: str, data: dict[str, str], headers: dict[str, str]) -> Any:
        body = urllib.parse.urlencode(data).encode('utf-8')
        request = urllib.request.Request(url, data=body, headers=headers, method='POST')
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode('utf-8'))

    def put_json(self, url: str, data: dict[str, Any], headers: dict[str, str]) -> str:
        body = json.dumps(data).encode('utf-8')
        request = urllib.request.Request(url, data=body, headers=headers, method='PUT')
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode('utf-8')

    def put_text(self, url: str, headers: dict[str, str]) -> str:
        request = urllib.request.Request(url, headers=headers, method='PUT')
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode('utf-8')

    def delete(self, url: str, headers: dict[str, str]) -> str:
        request = urllib.request.Request(url, headers=headers, method='DELETE')
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode('utf-8')


class MinifluxClient:
    def __init__(self, config: RssAccountConfig, http_client: Optional[_JsonHttpClient] = None):
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
                )
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

    def update_entry(self, external_entry_id: str, is_read: Optional[bool] = None, is_starred: Optional[bool] = None) -> None:
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

    def subscribe(self, feed_url: str, category_id: Optional[int] = None) -> RemoteFeed:
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


class FeverClient:
    def __init__(self, config: RssAccountConfig, http_client: Optional[_JsonHttpClient] = None):
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
                )
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

    def update_entry(self, external_entry_id: str, is_read: Optional[bool] = None, is_starred: Optional[bool] = None) -> None:
        if is_read is not None:
            self._post({
                'mark': 'item',
                'as': 'read' if is_read else 'unread',
                'id': str(external_entry_id)
            })
        if is_starred is not None:
            self._post({
                'mark': 'item',
                'as': 'saved' if is_starred else 'unsaved',
                'id': str(external_entry_id)
            })

    def subscribe(self, feed_url: str) -> RemoteFeed:
        raise RssServiceError('Fever API does not support subscribing to feeds')

    def unsubscribe(self, external_feed_id: str) -> None:
        raise RssServiceError('Fever API does not support unsubscribing from feeds')


class GReaderClient:
    def __init__(self, config: RssAccountConfig, http_client: Optional[_JsonHttpClient] = None):
        self.config = config
        self.http_client = http_client or _JsonHttpClient()
        self._auth_token: Optional[str] = None

    def _headers(self) -> dict[str, str]:
        return {
            'Accept': 'application/json',
            'Authorization': f'GoogleLogin auth={self._login()}',
            'User-Agent': 'Squirrel/1.0',
        }

    def _login(self) -> str:
        if self._auth_token:
            return self._auth_token
        if not self.config.username:
            raise RssServiceError('Google Reader API username is required')

        response = self.http_client.post_text(
            f'{self.config.base_url}/accounts/ClientLogin',
            {
                'Email': self.config.username,
                'Passwd': self.config.credential,
            },
            {
                'Accept': 'text/plain',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Squirrel/1.0',
            },
        )
        for line in response.splitlines():
            key, separator, value = line.partition('=')
            if separator and key == 'Auth' and value.strip():
                self._auth_token = value.strip()
                return self._auth_token
        raise RssServiceError('Google Reader API authentication failed')

    def list_feeds(self) -> list[RemoteFeed]:
        data = self.http_client.get_json(
            f'{self.config.base_url}/reader/api/0/subscription/list?output=json',
            self._headers(),
        )
        subscriptions = data.get('subscriptions') if isinstance(data, dict) else None
        if not isinstance(subscriptions, list):
            raise RssServiceError('Invalid Google Reader API subscriptions response')

        feeds: list[RemoteFeed] = []
        for item in subscriptions:
            if not isinstance(item, dict):
                continue
            feed_id = str(item.get('id') or '').strip()
            if not feed_id:
                continue
            feed_url = item.get('url')
            if not feed_url and feed_id.startswith('feed/'):
                feed_url = feed_id[5:]
            feeds.append(
                RemoteFeed(
                    external_feed_id=feed_id,
                    title=str(item.get('title') or feed_url or feed_id),
                    feed_url=feed_url,
                    site_url=item.get('htmlUrl'),
                    icon_url=item.get('iconUrl'),
                    category=_greader_category_label(item.get('categories')),
                    raw_data=dict(item),
                )
            )
        return feeds

    def list_entries(self, external_feed_id: str, limit: int) -> list[RemoteEntry]:
        stream_id = urllib.parse.quote(str(external_feed_id), safe='/')
        result: list[RemoteEntry] = []
        for page in self._iter_stream_entries(stream_id, limit):
            result.extend(page)
            if limit is not None and len(result) >= limit:
                break
        return result[:limit] if limit is not None else result

    def list_recent_entries(
        self,
        limit: Optional[int],
        progress_callback: Optional[Callable[[int, Optional[str]], None]] = None,
    ) -> list[RemoteEntry]:
        result: list[RemoteEntry] = []
        for page in self._iter_stream_entries('reading-list', limit, progress_callback):
            result.extend(page)
        return result[:limit] if limit is not None else result

    def iter_recent_entries(
        self,
        limit: Optional[int],
        progress_callback: Optional[Callable[[int, Optional[str]], None]] = None,
    ) -> Iterator[list[RemoteEntry]]:
        return self._iter_stream_entries('reading-list', limit, progress_callback)

    def _iter_stream_entries(
        self,
        stream_id: str,
        limit: Optional[int],
        progress_callback: Optional[Callable[[int, Optional[str]], None]] = None,
    ) -> Iterator[list[RemoteEntry]]:
        fetched = 0
        continuation: Optional[str] = None

        while True:
            page_size = G_READER_PAGE_SIZE if limit is None else min(G_READER_PAGE_SIZE, max(1, limit - fetched))
            query_params = {'output': 'json', 'n': str(page_size)}
            if continuation:
                query_params['c'] = continuation
            query = urllib.parse.urlencode(query_params)
            data = self.http_client.get_json(
                f'{self.config.base_url}/reader/api/0/stream/contents/{stream_id}?{query}',
                self._headers(),
            )
            items = data.get('items') if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise RssServiceError('Invalid Google Reader API stream response')
            page = [_greader_entry_to_remote(item) for item in items if isinstance(item, dict)]
            fetched += len(page)
            continuation = str(data.get('continuation') or '').strip()
            if progress_callback:
                progress_callback(fetched, continuation or None)
            if page:
                yield page
            if limit is not None and fetched >= limit:
                break
            if not items or not continuation:
                break

    def fetch_all_item_ids(self, stream_id: str = 'reading-list', limit: int = 200000) -> list[str]:
        params = {'output': 'json', 's': stream_id, 'n': str(limit)}
        data = self.http_client.get_json(
            f'{self.config.base_url}/reader/api/0/stream/items/ids?{urllib.parse.urlencode(params)}',
            self._headers(),
        )
        if not isinstance(data, dict):
            return []
        ids = data.get('itemRefs') or data.get('itemIds')
        if isinstance(ids, list):
            return [str(i.get('id') if isinstance(i, dict) else i) for i in ids if i]
        items = data.get('items')
        if isinstance(items, list):
            return [str(i.get('id', '')) for i in items if isinstance(i, dict) and i.get('id')]
        return []

    def fetch_unread_item_ids(self, limit: int = 200000) -> list[str]:
        params = {
            'output': 'json',
            's': 'reading-list',
            'xt': G_READER_READ_STATE,
            'n': str(limit),
        }
        data = self.http_client.get_json(
            f'{self.config.base_url}/reader/api/0/stream/items/ids?{urllib.parse.urlencode(params)}',
            self._headers(),
        )
        if not isinstance(data, dict):
            return []
        ids = data.get('itemRefs') or data.get('itemIds')
        if isinstance(ids, list):
            return [str(i.get('id') if isinstance(i, dict) else i) for i in ids if i]
        items = data.get('items')
        if isinstance(items, list):
            return [str(i.get('id', '')) for i in items if isinstance(i, dict) and i.get('id')]
        return []

    def fetch_items_contents(self, entry_ids: list[str]) -> list[RemoteEntry]:
        base = f'{self.config.base_url}/reader/api/0/stream/items/contents?output=json'
        body = urllib.parse.urlencode([('i', eid) for eid in entry_ids])
        data = self.http_client.post_text(base, body, {
            'Authorization': self._headers()['Authorization'],
            'Content-Type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Squirrel/1.0',
        })
        items = json.loads(data).get('items') if data else None
        if not isinstance(items, list):
            return []
        return [_greader_entry_to_remote(item) for item in items if isinstance(item, dict)]

    def test_connection(self) -> int:
        return len(self.list_feeds())

    def _get_token(self) -> str:
        url = f'{self.config.base_url}/reader/api/0/token'
        request = urllib.request.Request(url, headers=self._headers(), method='GET')
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode('utf-8').strip()

    def update_entry(self, external_entry_id: str, is_read: Optional[bool] = None, is_starred: Optional[bool] = None) -> None:
        try:
            token = self._get_token()
        except Exception as e:
            logger.warning('Failed to fetch GReader token for updating entry status: %s', e)
            return

        headers = self._headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'

        if is_read is not None:
            data = {
                'i': external_entry_id,
                'T': token,
                'a' if is_read else 'r': 'user/-/state/com.google/read'
            }
            self.http_client.post_text(f'{self.config.base_url}/reader/api/0/edit-tag', data, headers)

        if is_starred is not None:
            data = {
                'i': external_entry_id,
                'T': token,
                'a' if is_starred else 'r': 'user/-/state/com.google/starred'
            }
            self.http_client.post_text(f'{self.config.base_url}/reader/api/0/edit-tag', data, headers)

    def subscribe(self, feed_url: str) -> RemoteFeed:
        try:
            token = self._get_token()
        except Exception as e:
            raise RssServiceError(f'Failed to fetch GReader token for subscribe: {e}') from e

        headers = self._headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self.http_client.post_text(
            f'{self.config.base_url}/reader/api/0/subscription/quickadd',
            {'quickadd': feed_url, 'T': token},
            headers,
        )

        stream_id = f'feed/{feed_url}'
        return RemoteFeed(
            external_feed_id=stream_id,
            title=feed_url,
            feed_url=feed_url,
        )

    def unsubscribe(self, external_feed_id: str) -> None:
        try:
            token = self._get_token()
        except Exception as e:
            raise RssServiceError(f'Failed to fetch GReader token for unsubscribe: {e}') from e

        headers = self._headers()
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        self.http_client.post_text(
            f'{self.config.base_url}/reader/api/0/subscription/edit',
            {'ac': 'unsubscribe', 's': external_feed_id, 'T': token},
            headers,
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


def _greader_entry_to_remote(item: dict[str, Any]) -> RemoteEntry:
    origin = item.get('origin')
    origin_url = origin.get('htmlUrl') if isinstance(origin, dict) else None
    origin_stream_id = origin.get('streamId') if isinstance(origin, dict) else None
    url = _greader_alternate_url(item) or str(origin_url or '').strip()
    entry_id = str(item.get('id') or url).strip()
    categories = item.get('categories') if isinstance(item.get('categories'), list) else []
    category_set = {str(category) for category in categories}
    return RemoteEntry(
        external_entry_id=entry_id,
        canonical_url=url or entry_id,
        title=str(item.get('title') or url or entry_id),
        external_feed_id=str(origin_stream_id).strip() if origin_stream_id else None,
        summary=_greader_text(item.get('content')) or _greader_text(item.get('summary')),
        author=item.get('author'),
        published_at=_parse_datetime(item.get('published') or item.get('updated') or item.get('crawlTimeMsec')),
        is_read=G_READER_READ_STATE in category_set,
        is_starred=G_READER_STARRED_STATE in category_set,
        raw_data=dict(item),
    )


def _greader_category_label(categories: Any) -> Optional[str]:
    if not isinstance(categories, list):
        return None
    for item in categories:
        if isinstance(item, dict) and item.get('label'):
            return str(item['label'])
    return None


def _greader_alternate_url(item: dict[str, Any]) -> Optional[str]:
    alternates = item.get('alternate')
    if not isinstance(alternates, list):
        return None
    for alternate in alternates:
        if isinstance(alternate, dict) and alternate.get('href'):
            return str(alternate['href']).strip()
    return None


def _greader_text(value: Any) -> Optional[str]:
    if isinstance(value, dict):
        content = value.get('content')
        return str(content) if content is not None else None
    if isinstance(value, str):
        return value
    return None


def _client_for_config(config: RssAccountConfig):
    if config.provider == 'greader':
        return GReaderClient(config)
    if config.provider == 'miniflux':
        return MinifluxClient(config)
    if config.provider == 'fever':
        return FeverClient(config)
    raise RssServiceError(f'Unsupported RSS provider: {config.provider}')


def _config_from_account(account: RssAccount) -> RssAccountConfig:
    return RssAccountConfig(
        provider=account.provider,
        base_url=account.base_url,
        username=account.username,
        credential=_decrypt(account.credential_encrypted),
    )


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
    provider = _normalize_provider(provider)
    base_url = _normalize_base_url(base_url)
    sync_entry_limit = _normalize_sync_entry_limit(provider, sync_entry_limit)
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
            credential_encrypted=_encrypt(credential),
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
    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            return None
        if provider is not None:
            account.provider = _normalize_provider(provider)
        if sync_entry_limit is not UNSET:
            account.sync_entry_limit = _normalize_sync_entry_limit(account.provider, sync_entry_limit)
        elif provider is not None:
            account.sync_entry_limit = _normalize_sync_entry_limit(account.provider, account.sync_entry_limit)
        if name is not None:
            normalized_name = str(name or '').strip()
            if not normalized_name:
                raise RssServiceError('Account name is required')
            account.name = normalized_name
        if base_url is not None:
            account.base_url = _normalize_base_url(base_url)
        if username is not None:
            account.username = str(username or '').strip() or None
        if credential is not None and str(credential).strip():
            account.credential_encrypted = _encrypt(str(credential).strip())
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
    config = RssAccountConfig(
        provider=_normalize_provider(provider),
        base_url=_normalize_base_url(base_url),
        username=str(username or '').strip() or None,
        credential=str(credential or '').strip(),
    )
    if not config.credential:
        raise RssServiceError('Credential is required')
    feed_count = _client_for_config(config).test_connection()
    return {'ok': True, 'feed_count': feed_count}


def test_account(user_id: int, account_id: int) -> Optional[dict[str, Any]]:
    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            return None
        config = _config_from_account(account)
    feed_count = _client_for_config(config).test_connection()
    return {'ok': True, 'feed_count': feed_count}


def sync_account(user_id: int, account_id: int, *, entry_limit: Optional[int] = None, force_full_sync: bool = False) -> Optional[dict[str, Any]]:
    sync_lock = _sync_lock_for_account(account_id)
    if not sync_lock.acquire(blocking=False):
        raise RssServiceError('RSS account sync is already running')

    _set_sync_progress(
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
    synced_feeds = 0
    synced_entries = 0
    error_message = None

    try:
        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if not account:
                return None
            config = _config_from_account(account)
            configured_entry_limit = account.sync_entry_limit

        effective_entry_limit = entry_limit if entry_limit is not None else configured_entry_limit

        client = _client_for_config(config)
        _set_sync_progress(account_id, phase='feeds_fetching', message='Fetching RSS feeds')
        remote_feeds = client.list_feeds()
        _set_sync_progress(
            account_id,
            phase='feeds_saving',
            message='Saving RSS feeds',
            feeds_total=len(remote_feeds),
        )
        feed_refs: list[tuple[int, str, bool]] = []
        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if not account:
                return None
            account.last_error = None
            feeds = _upsert_feeds(session, account, remote_feeds)
            for index, feed in enumerate(feeds, start=1):
                feed_refs.append((feed.id, feed.external_feed_id, feed.enabled))
                if index % 50 == 0 or index == len(feeds):
                    _set_sync_progress(account_id, feeds_synced=index)
        synced_feeds = len(feeds)

        if isinstance(client, GReaderClient):
            greader_entry_limit = effective_entry_limit
            if not force_full_sync:
                quick_entry_limit = min(
                    G_READER_QUICK_MAX_ENTRIES,
                    max(1, len(feed_refs) * G_READER_QUICK_ENTRIES_PER_FEED),
                )
                greader_entry_limit = (
                    min(effective_entry_limit, quick_entry_limit)
                    if effective_entry_limit is not None
                    else quick_entry_limit
                )

            _set_sync_progress(
                account_id,
                phase='entries_fetching',
                message='Fetching RSS entries',
                entry_limit=greader_entry_limit,
            )

            def _on_entries_fetched(entry_count: int, continuation: Optional[str]) -> None:
                _set_sync_progress(
                    account_id,
                    phase='entries_fetching',
                    entries_fetched=entry_count,
                    has_more=bool(continuation),
                )

            with get_session() as session:
                feeds_by_external_id: dict[str, RssFeed] = {}
                for page in client.iter_recent_entries(greader_entry_limit, _on_entries_fetched):
                    new_feeds = _load_feeds_by_external_id(session, account_id, page, feeds_by_external_id)
                    feeds_by_external_id.update(new_feeds)
                    batch_entries = _upsert_remote_entries_batch(session, feeds_by_external_id, page)
                    synced_entries += batch_entries
                    _set_sync_progress(account_id, phase='entries_saving', entries_synced=synced_entries)
                    session.commit()
                    if not force_full_sync and batch_entries == 0:
                        break

            unread_ids = set(client.fetch_unread_item_ids(limit=200000))
            with get_session() as session:
                local_rows = session.execute(
                    select(RssEntry.id, RssEntry.external_entry_id, RssEntry.is_read)
                    .where(RssEntry.account_id == account_id)
                ).all()
                local_by_eid = {
                    row.external_entry_id: (row.id, row.is_read)
                    for row in local_rows
                }
                missing_unread_ids = list(unread_ids - set(local_by_eid.keys()))
                read_updates = []
                for external_entry_id, (entry_id, is_read) in local_by_eid.items():
                    should_read = external_entry_id not in unread_ids
                    if is_read != should_read:
                        read_updates.append({'id': entry_id, 'is_read': should_read})
                if read_updates:
                    session.bulk_update_mappings(RssEntry, read_updates)
                    session.commit()

            if missing_unread_ids:
                _set_sync_progress(account_id, phase='entries_fetching', message='Fetching unread RSS entries')
                with get_session() as session:
                    feeds_by_external_id: dict[str, RssFeed] = {}
                    for index in range(0, len(missing_unread_ids), G_READER_CONTENT_BATCH_SIZE):
                        chunk_ids = missing_unread_ids[index:index + G_READER_CONTENT_BATCH_SIZE]
                        page = [
                            replace(entry, is_read=False)
                            for entry in client.fetch_items_contents(chunk_ids)
                        ]
                        new_feeds = _load_feeds_by_external_id(session, account_id, page, feeds_by_external_id)
                        feeds_by_external_id.update(new_feeds)
                        batch_entries = _upsert_remote_entries_batch(session, feeds_by_external_id, page)
                        synced_entries += batch_entries
                        _set_sync_progress(account_id, phase='entries_saving', entries_synced=synced_entries)
                        session.commit()

            if force_full_sync:
                reading_ids_raw = client.fetch_all_item_ids('reading-list', limit=200000)
                if reading_ids_raw:
                    _set_sync_progress(account_id, phase='entries_saving', message='Syncing read/starred state')
                    read_ids = set(client.fetch_all_item_ids(G_READER_READ_STATE, limit=200000))
                    starred_ids = set(client.fetch_all_item_ids(G_READER_STARRED_STATE, limit=50000))
                    reading_ids = set(reading_ids_raw)

                    with get_session() as session:
                        local_rows = session.execute(
                            select(RssEntry.id, RssEntry.external_entry_id, RssEntry.is_read, RssEntry.is_starred)
                            .where(RssEntry.account_id == account_id)
                        ).all()

                        local_by_eid: dict[str, tuple[int, bool, bool]] = {
                            row.external_entry_id: (row.id, row.is_read, row.is_starred)
                            for row in local_rows
                        }

                        local_ids = set(local_by_eid.keys())
                        removed_ids = local_ids - reading_ids

                        if removed_ids:
                            session.execute(delete(RssEntry).where(
                                RssEntry.account_id == account_id,
                                RssEntry.external_entry_id.in_(list(removed_ids)),
                            ))

                        update_dicts: list[dict[str, Any]] = []
                        for eid, (eid_id, is_read, is_starred) in local_by_eid.items():
                            if eid not in reading_ids:
                                continue
                            should_read = eid in read_ids
                            should_starred = eid in starred_ids
                            if is_read != should_read or is_starred != should_starred:
                                update_dicts.append({'id': eid_id, 'is_read': should_read, 'is_starred': should_starred})

                        if update_dicts:
                            session.bulk_update_mappings(RssEntry, update_dicts)

                        if removed_ids or update_dicts:
                            session.commit()
        else:
            if effective_entry_limit is None:
                raise RssServiceError('Sync entry limit is required for this RSS provider')
            with get_session() as session:
                for feed_id, external_feed_id, enabled in feed_refs:
                    if not enabled:
                        continue
                    _set_sync_progress(
                        account_id,
                        phase='entries_fetching',
                        message='Fetching RSS entries',
                        current_feed_id=feed_id,
                        feeds_synced=synced_feeds,
                    )
                    remote_entries = client.list_entries(external_feed_id, effective_entry_limit)
                    feed = session.scalars(
                        select(RssFeed).where(
                            RssFeed.id == feed_id,
                            RssFeed.user_id == user_id,
                            RssFeed.account_id == account_id,
                        )
                    ).first()
                    if not feed:
                        continue
                    feeds_by_external_id = {external_feed_id: feed}
                    if remote_entries:
                        remote_entries = [replace(re, external_feed_id=re.external_feed_id or external_feed_id) for re in remote_entries]
                    batch_entries = _upsert_remote_entries_batch(session, feeds_by_external_id, remote_entries)
                    synced_entries += batch_entries
                    feed.last_entry_sync_at = datetime.now()
                    _set_sync_progress(
                        account_id,
                        phase='entries_saving',
                        entries_synced=synced_entries,
                    )
                    session.commit()

        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if account:
                account.last_sync_at = datetime.now()
                account.last_error = None
        _set_sync_progress(
            account_id,
            running=False,
            phase='completed',
            message='RSS sync completed',
            feeds_synced=synced_feeds,
            entries_synced=synced_entries,
            error=None,
            finished_at=datetime.now().isoformat(),
        )
    except Exception as exc:
        error_message = str(exc)
        provider = config.provider if 'config' in locals() else 'unknown'
        logger.warning('RSS account sync failed: account_id=%s provider=%s error=%s', account_id, provider, exc)
        with get_session() as session:
            account = _get_account(session, user_id, account_id)
            if account:
                account.last_error = error_message
                session.commit()
        _set_sync_progress(
            account_id,
            running=False,
            phase='failed',
            message='RSS sync failed',
            feeds_synced=synced_feeds,
            entries_synced=synced_entries,
            error=error_message,
            finished_at=datetime.now().isoformat(),
        )
        raise
    finally:
        sync_lock.release()

    return {
        'account_id': account_id,
        'feeds': synced_feeds,
        'entries': synced_entries,
        'error': error_message,
    }


def list_feeds(user_id: int, account_id: Optional[int] = None) -> list[dict[str, Any]]:
    with get_session() as session:
        statement = select(RssFeed).where(RssFeed.user_id == user_id)
        if account_id is not None:
            statement = statement.where(RssFeed.account_id == account_id)
        feeds = session.scalars(statement.order_by(RssFeed.title.asc())).all()
        return [serialize_feed(feed) for feed in feeds]


def subscribe_feed(
    user_id: int,
    account_id: int,
    feed_url: str,
    category: Optional[str] = None,
) -> dict[str, Any]:
    feed_url = str(feed_url or '').strip()
    if not feed_url:
        raise RssServiceError('Feed URL is required')
    parsed = urllib.parse.urlparse(feed_url)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise RssServiceError('Feed URL must be an HTTP or HTTPS URL')

    with get_session() as session:
        account = _get_account(session, user_id, account_id)
        if not account:
            raise RssServiceError('RSS account not found')

        config = _config_from_account(account)

        client = _client_for_config(config)
        remote_feed = client.subscribe(feed_url)

        existing = session.scalars(
            select(RssFeed).where(
                RssFeed.account_id == account_id,
                RssFeed.external_feed_id == remote_feed.external_feed_id,
            )
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
        return serialize_feed(feed)


def unsubscribe_feed(user_id: int, account_id: int, feed_id: int) -> bool:
    with get_session() as session:
        feed = session.scalars(
            select(RssFeed).where(
                RssFeed.id == feed_id,
                RssFeed.account_id == account_id,
                RssFeed.user_id == user_id,
            )
        ).first()
        if not feed:
            return False

        external_feed_id = feed.external_feed_id

    with get_session() as session:
        account = _get_account(session, user_id, account_id)

    if account and account.enabled:
        try:
            config = _config_from_account(account)
            client = _client_for_config(config)
            client.unsubscribe(external_feed_id)
        except RssServiceError:
            raise
        except Exception as e:
            logger.warning(
                'Failed to sync unsubscribe to remote RSS service: account_id=%s feed_id=%s error=%s',
                account_id, feed_id, e,
            )
            raise RssServiceError(f'Failed to unsubscribe from remote RSS service: {e}') from e

    with get_session() as session:
        feed = session.scalars(
            select(RssFeed).where(
                RssFeed.id == feed_id,
                RssFeed.account_id == account_id,
                RssFeed.user_id == user_id,
            )
        ).first()
        if not feed:
            return True

        entry_rows = session.execute(
            select(RssEntry.id).where(RssEntry.feed_id == feed_id)
        ).all()
        entry_ids = [row.id for row in entry_rows]
        if entry_ids:
            session.execute(
                delete(RssEntryView).where(RssEntryView.entry_id.in_(entry_ids))
            )
        session.execute(
            delete(RssEntry).where(RssEntry.feed_id == feed_id)
        )
        session.delete(feed)
        session.commit()

    return True


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

        # Remote sync-back to third-party RSS accounts
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
                    client = _client_for_config(config_data)
                    if hasattr(client, 'update_entry'):
                        client.update_entry(ext_eid, is_read=read_val, is_starred=star_val)
                except Exception as e:
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
                    _client_for_config(config).update_entry(external_entry_id, is_read=is_read)
                except Exception as e:
                    logger.warning('Failed to sync RSS read status to remote in background: %s', e)

        Thread(target=_bg_update_remote, daemon=True).start()

    return {'updated': len(changed_entries)}


def mark_feed_as_read(user_id: int, feed_id: int) -> dict[str, Any]:
    """Mark all unread entries of a specific feed as read and trigger sync with remote RSS server."""
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


def _get_account(session, user_id: int, account_id: int) -> Optional[RssAccount]:
    return session.scalars(
        select(RssAccount).where(
            RssAccount.id == account_id,
            RssAccount.user_id == user_id,
            RssAccount.is_deleted.is_(False),
        )
    ).first()


def _upsert_feeds(session, account: RssAccount, remotes: list[RemoteFeed]) -> list[RssFeed]:
    external_feed_ids = [r.external_feed_id for r in remotes]
    existing_by_id: dict[str, RssFeed] = {}
    if external_feed_ids:
        existing_rows = session.scalars(
            select(RssFeed).where(
                RssFeed.account_id == account.id,
                RssFeed.external_feed_id.in_(external_feed_ids),
            )
        ).all()
        existing_by_id = {f.external_feed_id: f for f in existing_rows}

    feeds: list[RssFeed] = []
    for remote in remotes:
        feed = existing_by_id.get(remote.external_feed_id)
        if feed is None:
            feed = RssFeed(
                user_id=account.user_id,
                account_id=account.id,
                external_feed_id=remote.external_feed_id,
                title=remote.title,
                enabled=True,
            )
            session.add(feed)
            session.flush()

        feed.title = remote.title
        feed.feed_url = remote.feed_url
        feed.site_url = remote.site_url
        feed.icon_url = remote.icon_url
        feed.category = remote.category
        feed.raw_data = remote.raw_data
        feeds.append(feed)

    return feeds


def _upsert_remote_entries_batch(
    session,
    feeds_by_external_id: dict[str, RssFeed],
    remote_entries: list[RemoteEntry],
) -> int:
    feed_ids: set[int] = set()
    entry_ids: list[str] = []

    for remote_entry in remote_entries:
        if not remote_entry.external_feed_id:
            continue
        feed = feeds_by_external_id.get(remote_entry.external_feed_id)
        if not feed or not feed.enabled:
            continue
        feed_ids.add(feed.id)
        entry_ids.append(remote_entry.external_entry_id)

    existing: dict[tuple[int, str], RssEntry] = {}
    if feed_ids and entry_ids:
        existing_rows = session.scalars(
            select(RssEntry).where(
                RssEntry.feed_id.in_(feed_ids),
                RssEntry.external_entry_id.in_(entry_ids),
            )
        ).all()
        existing = {(e.feed_id, e.external_entry_id): e for e in existing_rows}

    new_dicts: list[dict[str, Any]] = []
    update_dicts: list[dict[str, Any]] = []
    touched_feeds: set[int] = set()
    now = datetime.now()

    for remote_entry in remote_entries:
        if not remote_entry.external_feed_id:
            continue
        feed = feeds_by_external_id.get(remote_entry.external_feed_id)
        if not feed or not feed.enabled:
            continue
        key = (feed.id, remote_entry.external_entry_id)
        entry = existing.get(key)

        common = dict(
            user_id=feed.user_id,
            account_id=feed.account_id,
            feed_id=feed.id,
            external_entry_id=remote_entry.external_entry_id,
            canonical_url=remote_entry.canonical_url,
            title=remote_entry.title,
            summary=remote_entry.summary,
            thumbnail=remote_entry.thumbnail,
            author=remote_entry.author,
            published_at=remote_entry.published_at,
            is_read=remote_entry.is_read,
            is_starred=remote_entry.is_starred,
            raw_data=remote_entry.raw_data,
        )

        if entry is None:
            common['created_at'] = now
            common['updated_at'] = now
            new_dicts.append(common)
        else:
            if (entry.title == remote_entry.title
                    and entry.summary == remote_entry.summary
                    and entry.author == remote_entry.author
                    and entry.canonical_url == remote_entry.canonical_url
                    and entry.thumbnail == remote_entry.thumbnail
                    and entry.is_read == remote_entry.is_read
                    and entry.is_starred == remote_entry.is_starred
                    and entry.published_at == remote_entry.published_at):
                continue

            common['id'] = entry.id
            common['updated_at'] = now
            update_dicts.append(common)

        if feed.id not in touched_feeds:
            feed.last_entry_sync_at = now
            touched_feeds.add(feed.id)

    if new_dicts:
        session.bulk_insert_mappings(RssEntry, new_dicts)
    if update_dicts:
        session.bulk_update_mappings(RssEntry, update_dicts)

    return len(new_dicts) + len(update_dicts)


def _load_feeds_by_external_id(
    session,
    account_id: int,
    remote_entries: list[RemoteEntry],
    known_feeds: Optional[dict[str, RssFeed]] = None,
) -> dict[str, RssFeed]:
    feed_ids = {entry.external_feed_id for entry in remote_entries if entry.external_feed_id}
    if not feed_ids:
        return {}
    if known_feeds:
        feed_ids -= known_feeds.keys()
    if not feed_ids:
        return {}
    feeds = session.scalars(
        select(RssFeed).where(
            RssFeed.account_id == account_id,
            RssFeed.external_feed_id.in_(sorted(feed_ids)),
        )
    ).all()
    return {feed.external_feed_id: feed for feed in feeds if feed.enabled}


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
