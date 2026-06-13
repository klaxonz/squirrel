from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from collections.abc import Callable, Iterator
from typing import Any

from ._base import (
    RemoteEntry,
    RemoteFeed,
    RssAccountConfig,
    RssServiceError,
    _JsonHttpClient,
    _parse_datetime,
)

logger = logging.getLogger(__name__)

G_READER_PAGE_SIZE = 1000
G_READER_CONTENT_BATCH_SIZE = 500
G_READER_QUICK_ENTRIES_PER_FEED = 10
G_READER_QUICK_MAX_ENTRIES = 1000
G_READER_READ_STATE = "user/-/state/com.google/read"
G_READER_STARRED_STATE = "user/-/state/com.google/starred"


class GReaderClient:
    def __init__(self, config: RssAccountConfig, http_client: _JsonHttpClient | None = None) -> None:
        self.config = config
        self.http_client = http_client or _JsonHttpClient()
        self._auth_token: str | None = None

    def _headers(self) -> dict[str, str]:
        return {
            "Accept": "application/json",
            "Authorization": f"GoogleLogin auth={self._login()}",
            "User-Agent": "Squirrel/1.0",
        }

    def _login(self) -> str:
        if self._auth_token:
            return self._auth_token
        if not self.config.username:
            raise RssServiceError("Google Reader API username is required")

        response = self.http_client.post_text(
            f"{self.config.base_url}/accounts/ClientLogin",
            {
                "Email": self.config.username,
                "Passwd": self.config.credential,
            },
            {
                "Accept": "text/plain",
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "Squirrel/1.0",
            },
        )
        for line in response.splitlines():
            key, separator, value = line.partition("=")
            if separator and key == "Auth" and value.strip():
                self._auth_token = value.strip()
                return self._auth_token
        raise RssServiceError("Google Reader API authentication failed")

    def list_feeds(self) -> list[RemoteFeed]:
        data = self.http_client.get_json(
            f"{self.config.base_url}/reader/api/0/subscription/list?output=json",
            self._headers(),
        )
        subscriptions = data.get("subscriptions") if isinstance(data, dict) else None
        if not isinstance(subscriptions, list):
            raise RssServiceError("Invalid Google Reader API subscriptions response")

        feeds: list[RemoteFeed] = []
        for item in subscriptions:
            if not isinstance(item, dict):
                continue
            feed_id = str(item.get("id") or "").strip()
            if not feed_id:
                continue
            feed_url = item.get("url")
            if not feed_url and feed_id.startswith("feed/"):
                feed_url = feed_id[5:]
            feeds.append(
                RemoteFeed(
                    external_feed_id=feed_id,
                    title=str(item.get("title") or feed_url or feed_id),
                    feed_url=feed_url,
                    site_url=item.get("htmlUrl"),
                    icon_url=item.get("iconUrl"),
                    category=_greader_category_label(item.get("categories")),
                    raw_data=dict(item),
                ),
            )
        return feeds

    def list_entries(self, external_feed_id: str, limit: int) -> list[RemoteEntry]:
        stream_id = urllib.parse.quote(str(external_feed_id), safe="/")
        result: list[RemoteEntry] = []
        for page in self._iter_stream_entries(stream_id, limit):
            result.extend(page)
            if limit is not None and len(result) >= limit:
                break
        return result[:limit] if limit is not None else result

    def list_recent_entries(
        self,
        limit: int | None,
        progress_callback: Callable[[int, str | None], None] | None = None,
    ) -> list[RemoteEntry]:
        result: list[RemoteEntry] = []
        for page in self._iter_stream_entries("reading-list", limit, progress_callback):
            result.extend(page)
        return result[:limit] if limit is not None else result

    def iter_recent_entries(
        self,
        limit: int | None,
        progress_callback: Callable[[int, str | None], None] | None = None,
    ) -> Iterator[list[RemoteEntry]]:
        return self._iter_stream_entries("reading-list", limit, progress_callback)

    def _iter_stream_entries(
        self,
        stream_id: str,
        limit: int | None,
        progress_callback: Callable[[int, str | None], None] | None = None,
    ) -> Iterator[list[RemoteEntry]]:
        fetched = 0
        continuation: str | None = None

        while True:
            page_size = G_READER_PAGE_SIZE if limit is None else min(G_READER_PAGE_SIZE, max(1, limit - fetched))
            query_params = {"output": "json", "n": str(page_size)}
            if continuation:
                query_params["c"] = continuation
            query = urllib.parse.urlencode(query_params)
            data = self.http_client.get_json(
                f"{self.config.base_url}/reader/api/0/stream/contents/{stream_id}?{query}",
                self._headers(),
            )
            items = data.get("items") if isinstance(data, dict) else None
            if not isinstance(items, list):
                raise RssServiceError("Invalid Google Reader API stream response")
            page = [_greader_entry_to_remote(item) for item in items if isinstance(item, dict)]
            fetched += len(page)
            continuation = str(data.get("continuation") or "").strip()
            if progress_callback:
                progress_callback(fetched, continuation or None)
            if page:
                yield page
            if limit is not None and fetched >= limit:
                break
            if not items or not continuation:
                break

    def fetch_all_item_ids(self, stream_id: str = "reading-list", limit: int = 200000) -> list[str]:
        params = {"output": "json", "s": stream_id, "n": str(limit)}
        data = self.http_client.get_json(
            f"{self.config.base_url}/reader/api/0/stream/items/ids?{urllib.parse.urlencode(params)}",
            self._headers(),
        )
        if not isinstance(data, dict):
            return []
        ids = data.get("itemRefs") or data.get("itemIds")
        if isinstance(ids, list):
            return [str(i.get("id") if isinstance(i, dict) else i) for i in ids if i]
        items = data.get("items")
        if isinstance(items, list):
            return [str(i.get("id", "")) for i in items if isinstance(i, dict) and i.get("id")]
        return []

    def fetch_unread_item_ids(self, limit: int = 200000) -> list[str]:
        params = {
            "output": "json",
            "s": "reading-list",
            "xt": G_READER_READ_STATE,
            "n": str(limit),
        }
        data = self.http_client.get_json(
            f"{self.config.base_url}/reader/api/0/stream/items/ids?{urllib.parse.urlencode(params)}",
            self._headers(),
        )
        if not isinstance(data, dict):
            return []
        ids = data.get("itemRefs") or data.get("itemIds")
        if isinstance(ids, list):
            return [str(i.get("id") if isinstance(i, dict) else i) for i in ids if i]
        items = data.get("items")
        if isinstance(items, list):
            return [str(i.get("id", "")) for i in items if isinstance(i, dict) and i.get("id")]
        return []

    def fetch_items_contents(self, entry_ids: list[str]) -> list[RemoteEntry]:
        base = f"{self.config.base_url}/reader/api/0/stream/items/contents?output=json"
        body = urllib.parse.urlencode([("i", eid) for eid in entry_ids])
        data = self.http_client.post_text(base, body, {
            "Authorization": self._headers()["Authorization"],
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Squirrel/1.0",
        })
        items = json.loads(data).get("items") if data else None
        if not isinstance(items, list):
            return []
        return [_greader_entry_to_remote(item) for item in items if isinstance(item, dict)]

    def test_connection(self) -> int:
        return len(self.list_feeds())

    def _get_token(self) -> str:
        url = f"{self.config.base_url}/reader/api/0/token"
        request = urllib.request.Request(url, headers=self._headers(), method="GET")
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8").strip()

    def update_entry(self, external_entry_id: str, is_read: bool | None = None, is_starred: bool | None = None) -> None:
        try:
            token = self._get_token()
        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to fetch GReader token for updating entry status: %s", e)
            return

        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"

        if is_read is not None:
            data = {
                "i": external_entry_id,
                "T": token,
                "a" if is_read else "r": "user/-/state/com.google/read",
            }
            self.http_client.post_text(f"{self.config.base_url}/reader/api/0/edit-tag", data, headers)

        if is_starred is not None:
            data = {
                "i": external_entry_id,
                "T": token,
                "a" if is_starred else "r": "user/-/state/com.google/starred",
            }
            self.http_client.post_text(f"{self.config.base_url}/reader/api/0/edit-tag", data, headers)

    def subscribe(self, feed_url: str) -> RemoteFeed:
        try:
            token = self._get_token()
        except (OSError, ValueError, TypeError) as e:
            raise RssServiceError(f"Failed to fetch GReader token for subscribe: {e}") from e

        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        self.http_client.post_text(
            f"{self.config.base_url}/reader/api/0/subscription/quickadd",
            {"quickadd": feed_url, "T": token},
            headers,
        )

        stream_id = f"feed/{feed_url}"
        return RemoteFeed(
            external_feed_id=stream_id,
            title=feed_url,
            feed_url=feed_url,
        )

    def unsubscribe(self, external_feed_id: str) -> None:
        try:
            token = self._get_token()
        except (OSError, ValueError, TypeError) as e:
            raise RssServiceError(f"Failed to fetch GReader token for unsubscribe: {e}") from e

        headers = self._headers()
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        self.http_client.post_text(
            f"{self.config.base_url}/reader/api/0/subscription/edit",
            {"ac": "unsubscribe", "s": external_feed_id, "T": token},
            headers,
        )


def _greader_entry_to_remote(item: dict[str, Any]) -> RemoteEntry:
    origin = item.get("origin")
    origin_url = origin.get("htmlUrl") if isinstance(origin, dict) else None
    origin_stream_id = origin.get("streamId") if isinstance(origin, dict) else None
    url = _greader_alternate_url(item) or str(origin_url or "").strip()
    entry_id = str(item.get("id") or url).strip()
    categories = item.get("categories") if isinstance(item.get("categories"), list) else []
    category_set = {str(category) for category in categories}
    return RemoteEntry(
        external_entry_id=entry_id,
        canonical_url=url or entry_id,
        title=str(item.get("title") or url or entry_id),
        external_feed_id=str(origin_stream_id).strip() if origin_stream_id else None,
        summary=_greader_text(item.get("content")) or _greader_text(item.get("summary")),
        author=item.get("author"),
        published_at=_parse_datetime(item.get("published") or item.get("updated") or item.get("crawlTimeMsec")),
        is_read=G_READER_READ_STATE in category_set,
        is_starred=G_READER_STARRED_STATE in category_set,
        raw_data=dict(item),
    )


def _greader_category_label(categories: Any) -> str | None:
    if not isinstance(categories, list):
        return None
    for item in categories:
        if isinstance(item, dict) and item.get("label"):
            return str(item["label"])
    return None


def _greader_alternate_url(item: dict[str, Any]) -> str | None:
    alternates = item.get("alternate")
    if not isinstance(alternates, list):
        return None
    for alternate in alternates:
        if isinstance(alternate, dict) and alternate.get("href"):
            return str(alternate["href"]).strip()
    return None


def _greader_text(value: Any) -> str | None:
    if isinstance(value, dict):
        content = value.get("content")
        return str(content) if content is not None else None
    if isinstance(value, str):
        return value
    return None
