import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, List, Any

from core.site_config_manager import apply_site_config_overrides, build_runtime_site_catalog, get_effective_site_catalog
from utils.site_catalog import SiteCatalog
from common.site_constants import (
    SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD,
    SITE_META_OFFLINE_THUMBNAILS_DISPLAY,
)


ALLOWED_OVERRIDE_KEYS = {
    'enabled',
    'aliases',
    'http',
    'proxy',
    'login',
    'rate_limit',
    'metadata',
    'cookie',
    'test_url',
    'icon_url',
    'label',
}


def _config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config" / "sites.json"


def _parse_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return True
    if isinstance(value, (int, float)):
        return bool(value)
    s = str(value).strip().lower()
    if s in {"true", "1", "yes", "y", "on"}:
        return True
    if s in {"false", "0", "no", "n", "off"}:
        return False
    return True


def _normalize_list(values: Any, field_name: str, allow_empty: bool = True) -> List[str]:
    if values is None:
        values = []
    if not isinstance(values, list):
        raise ValueError(f"{field_name} 必须是数组")
    cleaned: List[str] = []
    for item in values:
        text = str(item).strip().lower()
        if text and text not in cleaned:
            cleaned.append(text)
    if not allow_empty and not cleaned:
        raise ValueError(f"{field_name} 不能为空")
    return cleaned


def _normalize_headers(values: Any, field_name: str) -> Dict[str, str]:
    if values is None:
        return {}
    if not isinstance(values, dict):
        raise ValueError(f"{field_name} 必须是对象")
    headers: Dict[str, str] = {}
    for key, val in values.items():
        if key is None:
            continue
        name = str(key).strip()
        if not name:
            continue
        if val is None:
            continue
        headers[name] = str(val)
    return headers


def _normalize_proxy(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("proxy 必须是对象")
    result: Dict[str, Any] = {}
    float_fields = [
        "connect_timeout",
        "read_timeout",
        "write_timeout",
        "pool_timeout",
        "keepalive_expiry",
    ]
    int_fields = [
        "max_retries",
        "chunk_size",
        "max_connections",
        "max_keepalive_connections",
    ]
    bool_fields = ["enable_http2", "follow_redirects"]
    for field in float_fields:
        value = raw.get(field)
        if value in (None, ""):
            continue
        result[field] = float(value)
    for field in int_fields:
        value = raw.get(field)
        if value in (None, ""):
            continue
        result[field] = int(value)
    for field in bool_fields:
        if field in raw:
            result[field] = _parse_bool(raw.get(field))
    return result


def _normalize_rate_limit(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("rate_limit 必须是对象")
    result: Dict[str, Any] = {}
    if "enabled" in raw:
        result["enabled"] = _parse_bool(raw.get("enabled"))
    min_interval = raw.get("min_interval")
    max_interval = raw.get("max_interval")
    if min_interval not in (None, ""):
        result["min_interval"] = float(min_interval)
    if max_interval not in (None, ""):
        result["max_interval"] = float(max_interval)
    return result


def _normalize_login(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("login 必须是对象")
    result: Dict[str, Any] = {}
    check_url = str(raw.get("check_url") or "").strip()
    if check_url:
        result["check_url"] = check_url
    headers = _normalize_headers(raw.get("headers"), "login.headers")
    if headers:
        result["headers"] = headers
    timeout = raw.get("timeout")
    if timeout not in (None, ""):
        result["timeout"] = float(timeout)
    if raw.get("extra_cookies"):
        result["extra_cookies"] = str(raw.get("extra_cookies")).strip()
    return result


def _normalize_metadata(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("metadata 必须是对象")
    result: Dict[str, Any] = {}
    for key in ("nsfw", "requires_login", "requires_cookies"):
        if key in raw:
            result[key] = _parse_bool(raw.get(key))

    if SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD in raw:
        result[SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD] = _parse_bool(raw.get(SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD))
    if SITE_META_OFFLINE_THUMBNAILS_DISPLAY in raw:
        result[SITE_META_OFFLINE_THUMBNAILS_DISPLAY] = _parse_bool(raw.get(SITE_META_OFFLINE_THUMBNAILS_DISPLAY))
    return result


def _normalize_cookie(raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError('cookie 必须是对象')
    result: Dict[str, Any] = {}
    alias_domains = _normalize_list(raw.get('alias_domains'), 'cookie.alias_domains')
    if alias_domains:
        result['alias_domains'] = alias_domains
    match_domain = str(raw.get('match_domain') or '').strip().lower().lstrip('.')
    if match_domain:
        result['match_domain'] = match_domain
    return result


def _normalize_override_entry(slug: str, raw: Any) -> Dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(f'{slug} 的配置必须是对象')

    unknown_keys = sorted(set(raw.keys()) - ALLOWED_OVERRIDE_KEYS)
    if unknown_keys:
        raise ValueError(f"{slug} 包含不支持的字段: {', '.join(unknown_keys)}")

    site_entry: Dict[str, Any] = {}

    if 'enabled' in raw:
        site_entry['enabled'] = _parse_bool(raw.get('enabled', True))

    if 'label' in raw:
        label = str(raw.get('label') or '').strip()
        if label:
            site_entry['label'] = label

    if 'aliases' in raw:
        site_entry['aliases'] = _normalize_list(raw.get('aliases'), f'{slug} 的别名')

    if 'http' in raw:
        http_section = raw.get('http') or {}
        if raw.get('http') not in (None, {}) and not isinstance(raw.get('http'), dict):
            raise ValueError('http 必须是对象')
        headers = _normalize_headers(http_section.get('headers'), f'{slug} 的 HTTP headers')
        site_entry['http'] = {'headers': headers} if headers else {}

    if 'proxy' in raw:
        site_entry['proxy'] = _normalize_proxy(raw.get('proxy'))

    if 'login' in raw:
        site_entry['login'] = _normalize_login(raw.get('login'))

    if 'rate_limit' in raw:
        site_entry['rate_limit'] = _normalize_rate_limit(raw.get('rate_limit'))

    if 'metadata' in raw:
        site_entry['metadata'] = _normalize_metadata(raw.get('metadata'))

    if 'cookie' in raw:
        site_entry['cookie'] = _normalize_cookie(raw.get('cookie'))

    if 'test_url' in raw:
        test_url = str(raw.get('test_url') or '').strip()
        if test_url:
            site_entry['test_url'] = test_url

    if 'icon_url' in raw:
        icon_url = str(raw.get('icon_url') or '').strip()
        if icon_url:
            site_entry['icon_url'] = icon_url

    return {key: value for key, value in site_entry.items() if value not in ({}, [], None)}


def _deep_merge_dicts(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    result = deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dicts(result.get(key, {}), value)
        else:
            result[key] = value
    return result


def _compute_override_diff(base: Dict[str, Any], desired: Dict[str, Any]) -> Dict[str, Any]:
    override: Dict[str, Any] = {}
    for key, desired_value in desired.items():
        base_value = base.get(key)
        if isinstance(desired_value, dict) and isinstance(base_value, dict):
            nested = _compute_override_diff(base_value, desired_value)
            if nested:
                override[key] = nested
            continue
        if desired_value != base_value:
            override[key] = desired_value
    return override


def save_site_overrides(overrides: Dict[str, dict]) -> Dict[str, dict]:
    if not isinstance(overrides, dict):
        raise ValueError('sites 必须为对象')

    plugin_catalog = build_runtime_site_catalog()
    existing_overrides = SiteCatalog.load_override_catalog() or {}
    current_effective = get_effective_site_catalog(existing_overrides)
    catalog: Dict[str, dict] = dict(existing_overrides)
    for raw_slug, raw in overrides.items():
        slug = str(raw_slug or '').strip().lower()
        if not slug:
            raise ValueError('站点标识不可为空')
        if slug not in plugin_catalog:
            raise ValueError(f'未知站点: {slug}')
        normalized_patch = _normalize_override_entry(slug, raw)
        desired_effective = _deep_merge_dicts(current_effective.get(slug, plugin_catalog[slug]), normalized_patch)
        normalized_entry = _compute_override_diff(plugin_catalog[slug], desired_effective)
        if normalized_entry:
            catalog[slug] = normalized_entry
        else:
            catalog.pop(slug, None)

    config_path = _config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        json.dumps(catalog, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    SiteCatalog.set_override_catalog(catalog)
    apply_site_config_overrides(catalog)
    return get_effective_site_catalog(catalog)
