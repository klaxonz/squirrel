from collections.abc import Iterable
from typing import Any

from utils.url_helper import get_site_from_url

SUGGESTION_POOL_MAX_ITEMS = 240


def normalize_query(value: str | None) -> str:
    return ' '.join(str(value or '').strip().split())


def serialize_video_meta(domain: str | None) -> str:
    if domain:
        site_name = get_site_from_url(f'https://{domain}')
        if site_name:
            return f'视频 · {site_name}'
    return '视频'


def serialize_rows(rows: Iterable[Any], source: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    seen: set[str] = set()

    for row in rows:
        value = normalize_query(getattr(row, 'value', None))
        if not value:
            continue

        dedupe_key = value.lower()
        if dedupe_key in seen:
            continue

        seen.add(dedupe_key)
        meta = normalize_query(getattr(row, 'meta', None))
        items.append({
            'type': source,
            'value': value,
            'label': value,
            'meta': meta,
        })

    return items


def dedupe_pool_items(items: Iterable[dict[str, str]]) -> list[dict[str, str]]:
    deduped: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()

    for item in items:
        value = normalize_query(item.get('value'))
        item_type = str(item.get('type') or '')
        dedupe_key = (item_type, value.lower())
        if not value or dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        deduped.append({
            'type': item_type,
            'value': value,
            'label': normalize_query(item.get('label') or value),
            'meta': normalize_query(item.get('meta') or ''),
        })
        if len(deduped) >= SUGGESTION_POOL_MAX_ITEMS:
            break

    return deduped

