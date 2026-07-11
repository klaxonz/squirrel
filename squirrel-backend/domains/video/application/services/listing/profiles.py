from __future__ import annotations

from domains.video.domain.models.video import Video


def _profile_key(profile: dict) -> tuple[str, str]:
    url = str(profile.get('url') or '').strip().lower()
    if url:
        return 'url', url

    profile_id = str(profile.get('id') or '').strip()
    if profile_id:
        return 'id', profile_id

    name = str(profile.get('name') or '').strip().lower()
    if name:
        return 'name', name

    return '', ''


def _merge_profile_fields(primary: dict, secondary: dict) -> dict:
    merged = dict(primary)
    for key, value in secondary.items():
        if value is None or value == '':
            continue
        if merged.get(key) is None or merged.get(key) == '':
            merged[key] = value
    return merged


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
            'profile_source': 'metadata',
        }
        if profile.get('description') is not None:
            item['description'] = profile.get('description')
        if profile.get('site') is not None:
            item['site'] = profile.get('site')
        normalized.append(item)

    return normalized


def merge_profiles(primary: list[dict], extra: list[dict]) -> list[dict]:
    merged = []
    index_by_key = {}
    for profile in [*primary, *extra]:
        key = _profile_key(profile)
        if key[0] and key in index_by_key:
            existing_index = index_by_key[key]
            merged[existing_index] = _merge_profile_fields(merged[existing_index], profile)
            continue
        merged.append(profile)
        if key[0]:
            index_by_key[key] = len(merged) - 1
    return merged
