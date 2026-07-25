from __future__ import annotations

import json
import logging
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter

logger = logging.getLogger(__name__)


class RssServiceError(ValueError):
    pass


@dataclass
class RssAccountConfig:
    provider: str
    base_url: str
    username: str | None
    credential: str


@dataclass
class RemoteFeed:
    external_feed_id: str
    title: str
    feed_url: str | None = None
    site_url: str | None = None
    icon_url: str | None = None
    category: str | None = None
    raw_data: dict[str, Any] = field(default_factory=dict)


@dataclass
class RemoteEntry:
    external_entry_id: str
    canonical_url: str
    title: str
    external_feed_id: str | None = None
    summary: str | None = None
    thumbnail: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    is_read: bool = False
    is_starred: bool = False
    raw_data: dict[str, Any] = field(default_factory=dict)


def _parse_datetime(value: Any) -> datetime | None:
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
    """Session-backed JSON client with connection reuse and bounded retries.

    FreshRSS/GReader sync issues many sequential HTTPS calls against the same host.
    Opening a fresh TLS handshake for each call regularly hit ``handshake timed out``
    / ``read operation timed out`` on flaky links and aborted the whole account sync.
    A shared ``requests.Session`` keeps the connection warm; retries stay local to one
    request so callers keep their own pagination/progress semantics.
    """

    def __init__(
        self,
        *,
        timeout: float = 60.0,
        retries: int = 3,
        retry_backoff_seconds: float = 0.5,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout = timeout
        self.retries = max(0, int(retries))
        self.retry_backoff_seconds = max(0.0, float(retry_backoff_seconds))
        self._session = session or self._build_session()

    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        # Keep a small pool so multi-page GReader fetches reuse the TLS socket.
        adapter = HTTPAdapter(pool_connections=4, pool_maxsize=4, max_retries=0)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def get_json(self, url: str, headers: dict[str, str]) -> Any:
        return self._request('GET', url, headers=headers).json()

    def get_text(self, url: str, headers: dict[str, str]) -> str:
        return self._request('GET', url, headers=headers).text

    def post_text(self, url: str, data: Mapping[str, Any] | Sequence[tuple[str, Any]], headers: dict[str, str]) -> str:
        return self._request('POST', url, headers=headers, data=data).text

    def post_json(self, url: str, data: dict[str, str], headers: dict[str, str]) -> Any:
        return self._request('POST', url, headers=headers, data=data).json()

    def put_json(self, url: str, data: dict[str, Any], headers: dict[str, str]) -> str:
        return self._request(
            'PUT',
            url,
            headers={**headers, 'Content-Type': 'application/json'},
            data=json.dumps(data),
        ).text

    def put_text(self, url: str, headers: dict[str, str]) -> str:
        return self._request('PUT', url, headers=headers).text

    def delete(self, url: str, headers: dict[str, str]) -> str:
        return self._request('DELETE', url, headers=headers).text

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        data: Any = None,
    ) -> requests.Response:
        attempts = self.retries + 1
        last_error: BaseException | None = None
        for attempt in range(attempts):
            try:
                response = self._session.request(
                    method,
                    url,
                    headers=headers,
                    data=data,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response
            except requests.HTTPError:
                # 4xx/5xx responses are application-level; do not retry.
                raise
            except (requests.RequestException, TimeoutError, OSError) as exc:
                last_error = exc
                if attempt + 1 >= attempts:
                    break
                delay = self.retry_backoff_seconds * (2**attempt)
                logger.warning(
                    'Transient RSS HTTP failure on %s %s (attempt %s/%s): %s; retrying in %.1fs',
                    method,
                    url,
                    attempt + 1,
                    attempts,
                    exc,
                    delay,
                )
                if delay > 0:
                    time.sleep(delay)
        assert last_error is not None
        raise RssServiceError(f'RSS service request failed: {last_error}') from last_error
