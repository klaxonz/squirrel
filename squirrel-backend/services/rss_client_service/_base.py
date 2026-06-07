from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

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
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except ValueError:
        return None


class _JsonHttpClient:
    def get_json(self, url: str, headers: dict[str, str]) -> Any:
        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def post_text(self, url: str, data: dict[str, str], headers: dict[str, str]) -> str:
        body = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")

    def post_json(self, url: str, data: dict[str, str], headers: dict[str, str]) -> Any:
        body = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(request, timeout=20) as response:
            return json.loads(response.read().decode("utf-8"))

    def put_json(self, url: str, data: dict[str, Any], headers: dict[str, str]) -> str:
        body = json.dumps(data).encode("utf-8")
        request = urllib.request.Request(url, data=body, headers=headers, method="PUT")
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")

    def put_text(self, url: str, headers: dict[str, str]) -> str:
        request = urllib.request.Request(url, headers=headers, method="PUT")
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")

    def delete(self, url: str, headers: dict[str, str]) -> str:
        request = urllib.request.Request(url, headers=headers, method="DELETE")
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read().decode("utf-8")
