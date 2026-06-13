from __future__ import annotations

from datetime import datetime
from typing import Any

from services.subscription.listing.site import resolve_site_slug


def serialize_datetime(dt: datetime | None) -> str:
    return dt.strftime('%Y-%m-%d %H:%M:%S') if dt else ''


def serialize_subscription_list_item(
    row: Any,
    total_extract: int,
    recent_videos: list[dict[str, Any]] | None = None,
    unread_count: int = 0,
) -> dict[str, Any]:
    row_data = row if isinstance(row, dict) else dict(row)
    total_videos = max(int(row_data['total_videos'] or 0), total_extract)
    url = row_data['url']

    return {
        'id': int(row_data['id']),
        'type': row_data['type'],
        'name': row_data['name'],
        'url': url,
        'avatar': row_data['avatar'],
        'description': row_data['description'],
        'total_videos': total_videos,
        'is_deleted': bool(row_data['is_deleted']),
        'extra_data': row_data['extra_data'],
        'created_at': serialize_datetime(row_data['created_at']),
        'updated_at': serialize_datetime(row_data['updated_at']),
        'is_nsfw': bool(row_data['is_nsfw']),
        'is_special_followed': bool(row_data['is_special_followed']),
        'total_extract': total_extract,
        'unread_count': unread_count,
        'sync_status': row_data['sync_status'] or 'idle',
        'last_sync_at': serialize_datetime(row_data['last_sync_at']),
        'last_success_at': serialize_datetime(row_data['last_success_at']),
        'next_sync_at': serialize_datetime(row_data['next_sync_at']),
        'last_error': row_data['last_error'],
        'pending_video_count': int(row_data['pending_video_count'] or 0),
        'site': resolve_site_slug(url),
        'recent_videos': recent_videos or [],
    }
