from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Any, Callable, Iterator, Optional

logger = logging.getLogger(__name__)

SUPPORTED_PROVIDERS = {'greader', 'miniflux', 'fever'}
G_READER_PAGE_SIZE = 1000
G_READER_CONTENT_BATCH_SIZE = 500
G_READER_QUICK_ENTRIES_PER_FEED = 10
G_READER_QUICK_MAX_ENTRIES = 1000
G_READER_READ_STATE = 'user/-/state/com.google/read'
G_READER_STARRED_STATE = 'user/-/state/com.google/starred'


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
    def __init__(self, config: RssAccountConfig, http_client: Optional[_JsonHttpClient] = None) -> None:
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
    def __init__(self, config: RssAccountConfig, http_client: Optional[_JsonHttpClient] = None) -> None:
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
    def __init__(self, config: RssAccountConfig, http_client: Optional[_JsonHttpClient] = None) -> None:
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
        except (OSError, ValueError, TypeError) as e:
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
        except (OSError, ValueError, TypeError) as e:
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
        except (OSError, ValueError, TypeError) as e:
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


def create_client(config: RssAccountConfig) -> MinifluxClient | FeverClient | GReaderClient:
    if config.provider == 'greader':
        return GReaderClient(config)
    if config.provider == 'miniflux':
        return MinifluxClient(config)
    if config.provider == 'fever':
        return FeverClient(config)
    raise RssServiceError(f'Unsupported RSS provider: {config.provider}')


def normalize_provider(provider: str) -> str:
    normalized = str(provider or '').strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise RssServiceError(f'Unsupported RSS provider: {provider}')
    return normalized


def normalize_base_url(base_url: str) -> str:
    normalized = str(base_url or '').strip().rstrip('/')
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise RssServiceError('RSS service URL must be an HTTP or HTTPS URL')
    return normalized


def normalize_sync_entry_limit(provider: str, sync_entry_limit: Optional[int]) -> Optional[int]:
    if sync_entry_limit is None:
        if provider == 'greader':
            return None
        raise RssServiceError('Sync entry limit is required for this RSS provider')
    limit = int(sync_entry_limit)
    if limit < 1:
        raise RssServiceError('Sync entry limit must be greater than 0')
    return limit