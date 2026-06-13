from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import format_image_url


def normalize_rank(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('rankid') or row.get('id') or ''),
        'rank_cid': str(row.get('rank_cid') or ''),
        'name': row.get('rankname') or '',
        'cover': format_image_url(row.get('imgurl') or row.get('album_img_9') or row.get('banner_9') or ''),
        'intro': row.get('intro') or '',
        'update_frequency': row.get('update_frequency') or '',
        'play_count': int(row.get('play_times') or 0),
    }
