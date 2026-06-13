from __future__ import annotations

from copy import copy
from typing import Any

from common.site_constants import (
    SITE_META_OFFLINE_THUMBNAILS_DISPLAY,
    SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD,
)

ALLOWED_OVERRIDE_KEYS = {
    'enabled', 'aliases', 'http', 'proxy', 'login',
    'rate_limit', 'metadata', 'cookie', 'test_url', 'icon_url', 'label',
}


def normalize_override_entry(slug: str, raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f'{slug} config must be a dict')

    unknown_keys = sorted(set(raw.keys()) - ALLOWED_OVERRIDE_KEYS)
    if unknown_keys:
        raise ValueError(f'{slug} has unsupported fields: {", ".join(unknown_keys)}')

    site_entry: dict[str, Any] = {}

    if 'enabled' in raw:
        site_entry['enabled'] = parse_bool(raw.get('enabled', True))
    if 'label' in raw:
        label = str(raw.get('label') or '').strip()
        if label:
            site_entry['label'] = label
    if 'aliases' in raw:
        site_entry['aliases'] = normalize_list(raw.get('aliases'), f'{slug} aliases')
    if 'http' in raw:
        http_section = raw.get('http') or {}
        if raw.get('http') not in (None, {}) and not isinstance(raw.get('http'), dict):
            raise ValueError('http must be a dict')
        headers = normalize_headers(http_section.get('headers'), f'{slug} HTTP headers')
        site_entry['http'] = {'headers': headers} if headers else {}
    if 'proxy' in raw:
        site_entry['proxy'] = normalize_proxy(raw.get('proxy'))
    if 'login' in raw:
        site_entry['login'] = normalize_login(raw.get('login'))
    if 'rate_limit' in raw:
        site_entry['rate_limit'] = normalize_rate_limit(raw.get('rate_limit'))
    if 'metadata' in raw:
        site_entry['metadata'] = normalize_metadata(raw.get('metadata'))
    if 'cookie' in raw:
        site_entry['cookie'] = normalize_cookie(raw.get('cookie'))
    if 'test_url' in raw:
        test_url = str(raw.get('test_url') or '').strip()
        if test_url:
            site_entry['test_url'] = test_url
    if 'icon_url' in raw:
        icon_url = str(raw.get('icon_url') or '').strip()
        if icon_url:
            site_entry['icon_url'] = icon_url

    return {k: v for k, v in site_entry.items() if v not in ({}, [], None)}


def deep_merge_dicts(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
    result = copy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = deep_merge_dicts(result.get(key, {}), value)
        else:
            result[key] = value
    return result


def compute_override_diff(base: dict[str, Any], desired: dict[str, Any]) -> dict[str, Any]:
    override: dict[str, Any] = {}
    for key, desired_value in desired.items():
        base_value = base.get(key)
        if isinstance(desired_value, dict) and isinstance(base_value, dict):
            nested = compute_override_diff(base_value, desired_value)
            if nested:
                override[key] = nested
            continue
        if desired_value != base_value:
            override[key] = desired_value
    return override


def parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    return s in {'true', '1', 'yes', 'y', 'on', ''}


def normalize_list(values: Any, field_name: str, allow_empty: bool = True) -> list[str]:
    if values is None:
        values = []
    if not isinstance(values, list):
        raise ValueError(f'{field_name} must be a list')
    cleaned: list[str] = []
    for item in values:
        text = str(item).strip().lower()
        if text and text not in cleaned:
            cleaned.append(text)
    if not allow_empty and not cleaned:
        raise ValueError(f'{field_name} cannot be empty')
    return cleaned


def normalize_headers(values: Any, field_name: str) -> dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError(f'{field_name} must be a dict')
    headers: dict[str, str] = {}
    for key, val in values.items():
        if key is None or val is None:
            continue
        name = str(key).strip()
        if name:
            headers[name] = str(val)
    return headers


def normalize_proxy(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('proxy must be a dict')
    normalized: dict[str, Any] = {}
    for field in ('connect_timeout', 'read_timeout', 'write_timeout', 'pool_timeout', 'keepalive_expiry'):
        value = raw.get(field)
        if value not in (None, ''):
            normalized[field] = float(value)
    for field in ('max_retries', 'chunk_size', 'max_connections', 'max_keepalive_connections'):
        value = raw.get(field)
        if value not in (None, ''):
            normalized[field] = int(value)
    if 'enable_http2' in raw:
        normalized['enable_http2'] = parse_bool(raw['enable_http2'])
    if 'follow_redirects' in raw:
        normalized['follow_redirects'] = parse_bool(raw['follow_redirects'])
    return normalized


def normalize_rate_limit(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('rate_limit must be a dict')
    normalized: dict[str, Any] = {}
    if 'enabled' in raw:
        normalized['enabled'] = parse_bool(raw['enabled'])
    min_interval = raw.get('min_interval')
    max_interval = raw.get('max_interval')
    if min_interval not in (None, ''):
        normalized['min_interval'] = float(min_interval)
    if max_interval not in (None, ''):
        normalized['max_interval'] = float(max_interval)
    return normalized


def normalize_login(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('login must be a dict')
    normalized: dict[str, Any] = {}
    check_url = str(raw.get('check_url') or '').strip()
    if check_url:
        normalized['check_url'] = check_url
    headers = normalize_headers(raw.get('headers'), 'login.headers')
    if headers:
        normalized['headers'] = headers
    timeout = raw.get('timeout')
    if timeout not in (None, ''):
        normalized['timeout'] = float(timeout)
    if raw.get('extra_cookies'):
        normalized['extra_cookies'] = str(raw.get('extra_cookies')).strip()
    return normalized


def normalize_metadata(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('metadata must be a dict')
    normalized: dict[str, Any] = {}
    for key in ('nsfw', 'requires_login', 'requires_cookies'):
        if key in raw:
            normalized[key] = parse_bool(raw[key])
    if SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD in raw:
        normalized[SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD] = parse_bool(raw[SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD])
    if SITE_META_OFFLINE_THUMBNAILS_DISPLAY in raw:
        normalized[SITE_META_OFFLINE_THUMBNAILS_DISPLAY] = parse_bool(raw[SITE_META_OFFLINE_THUMBNAILS_DISPLAY])
    return normalized


def normalize_cookie(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('cookie must be a dict')
    normalized: dict[str, Any] = {}
    alias_domains = normalize_list(raw.get('alias_domains'), 'cookie.alias_domains')
    if alias_domains:
        normalized['alias_domains'] = alias_domains
    match_domain = str(raw.get('match_domain') or '').strip().lower().lstrip('.')
    if match_domain:
        normalized['match_domain'] = match_domain
    return normalized
