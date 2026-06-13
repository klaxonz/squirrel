from __future__ import annotations

from domains.video.domain.models.video import Video


def video_extra_profiles(video: Video, key: str) -> list[dict]:
    extra_data = video.extra_data if isinstance(video.extra_data, dict) else {}
    profiles = extra_data.get(key)
    if not isinstance(profiles, list):
        return []

    normalized = []
    for profile in profiles:
        if not isinstance(profile, dict):
            continue
        name = str(profile.get('name') or '').strip()
        url = str(profile.get('url') or '').strip()
        if not name and not url:
            continue
        item = {
            'id': profile.get('id'),
            'name': name,
            'url': url,
            'type': profile.get('type'),
            'avatar': profile.get('avatar'),
            'is_nsfw': profile.get('is_nsfw'),
        }
        if profile.get('description') is not None:
            item['description'] = profile.get('description')
        if profile.get('site') is not None:
            item['site'] = profile.get('site')
        normalized.append(item)

    return normalized


def merge_profiles(primary: list[dict], extra: list[dict]) -> list[dict]:
    merged = []
    seen = set()
    for profile in [*primary, *extra]:
        key = (
            str(profile.get('id') or '').strip(),
            str(profile.get('url') or '').strip(),
            str(profile.get('name') or '').strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        merged.append(profile)
    return merged
