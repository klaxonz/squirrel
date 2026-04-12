import logging
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from core.config import settings
from core.cookie_config import get_site_cookies_dir, get_site_cookies_file_path, write_cookie_text_file
from core.site_config_manager import get_effective_site_catalog

logger = logging.getLogger(__name__)


class CookieCloudSyncError(RuntimeError):
    pass


_YOUTUBE_LOGGED_FLAG = re.compile(r'"LOGGED_IN":\s*(true|false)', re.IGNORECASE)
_YOUTUBE_LOGIN_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}


def _get_cookiecloud_config() -> Tuple[str, str, str]:
    url = (settings.COOKIECLOUD_URL or "").strip()
    uuid = (settings.COOKIECLOUD_UUID or "").strip()
    password = (settings.COOKIECLOUD_PASSWORD or "").strip()
    return url, uuid, password


def is_cookiecloud_configured() -> bool:
    url, uuid, password = _get_cookiecloud_config()
    return bool(url and uuid and password)


def fetch_cookiecloud_cookie_data() -> Dict[str, Any]:
    url, uuid, password = _get_cookiecloud_config()
    if not url or not uuid or not password:
        raise CookieCloudSyncError(
            "CookieCloud 未配置，请设置 COOKIECLOUD_URL / COOKIECLOUD_UUID / COOKIECLOUD_PASSWORD"
        )

    try:
        from PyCookieCloud import PyCookieCloud
    except Exception as exc:
        raise CookieCloudSyncError(f"缺少依赖 PyCookieCloud: {exc}") from exc

    client = PyCookieCloud(url=url, uuid=uuid, password=password)
    data = client.get_decrypted_data()
    if not isinstance(data, dict) or not data:
        raise CookieCloudSyncError("CookieCloud 返回为空或解密失败")
    return data


def _normalize_domain(domain: str) -> str:
    if not domain:
        return ""
    d = str(domain).strip()
    if d.startswith("#HttpOnly_"):
        d = d[len("#HttpOnly_") :]
    return d.lstrip(".").lower()


def _domain_matches(cookie_domain: str, site_domain: str) -> bool:
    if not cookie_domain or not site_domain:
        return False
    if cookie_domain == site_domain:
        return True
    return cookie_domain.endswith("." + site_domain)


def _to_int_seconds(value: Any) -> int:
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except Exception:
        return 0


def _cookie_to_netscape_line(cookie: Dict[str, Any]) -> Optional[str]:
    name = cookie.get("name")
    value = cookie.get("value")
    raw_domain = cookie.get("domain")
    if not name or value is None or not raw_domain:
        return None

    domain_clean = str(raw_domain).strip()
    http_only = bool(cookie.get("httpOnly", False))
    host_only = cookie.get("hostOnly")

    include_subdomains: bool
    if host_only is True:
        include_subdomains = False
    elif host_only is False:
        include_subdomains = True
    else:
        include_subdomains = domain_clean.startswith(".")

    domain_no_dot = domain_clean.lstrip(".")
    domain_out = f".{domain_no_dot}" if include_subdomains else domain_no_dot
    if http_only:
        domain_out = f"#HttpOnly_{domain_out}"

    flag_out = "TRUE" if include_subdomains else "FALSE"
    path_out = str(cookie.get("path") or "/")
    secure_out = "TRUE" if bool(cookie.get("secure", False)) else "FALSE"
    expires_out = str(_to_int_seconds(cookie.get("expirationDate")))

    return "\t".join([domain_out, flag_out, path_out, secure_out, expires_out, str(name), str(value)])


def _write_candidate_cookie_file(lines: list[str]) -> Path:
    temp_file = tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8')
    try:
        temp_file.write('\n'.join(lines) + '\n')
        temp_file.flush()
    finally:
        temp_file.close()
    return Path(temp_file.name)


def _validate_youtube_cookie_lines(lines: list[str]) -> Optional[str]:
    try:
        from crawl import filter_cookies_to_query_string, get_login_config, get_login_headers, request_without_limit
    except Exception as exc:
        return f'validator bootstrap failed: {exc}'

    candidate_path = _write_candidate_cookie_file(lines)
    try:
        login_config = get_login_config('youtube')
        check_url = login_config.get('check_url') or 'https://www.youtube.com/feed/channels'
        cookie_header = filter_cookies_to_query_string(check_url, cookies_file=str(candidate_path))
        if not cookie_header:
            return 'candidate file does not contain any usable youtube cookies'

        headers = get_login_headers('youtube', _YOUTUBE_LOGIN_HEADERS)
        headers['Cookie'] = cookie_header
        timeout = float(login_config.get('timeout', 20))
        response = request_without_limit('GET', check_url, headers=headers, timeout=timeout)
        body = response.text or ''
        match = _YOUTUBE_LOGGED_FLAG.search(body)
        if match and match.group(1).lower() == 'true':
            return None
        return f'youtube login check rejected candidate cookies: url={response.url or check_url}'
    except Exception as exc:
        return f'youtube login check failed: {exc}'
    finally:
        try:
            os.remove(candidate_path)
        except OSError:
            pass


def _validate_cookie_lines_for_site(site_slug: str, lines: list[str]) -> Optional[str]:
    if str(site_slug or '').strip().lower() == 'youtube':
        return _validate_youtube_cookie_lines(lines)
    return None


def sync_cookiecloud_to_site_files(site_slug: Optional[str] = None) -> Dict[str, Any]:
    cookie_data = fetch_cookiecloud_cookie_data()
    catalog = get_effective_site_catalog()

    site_domains: Dict[str, list[str]] = {}
    for slug, info in catalog.items():
        if site_slug and slug.lower() != site_slug.strip().lower():
            continue
        domains = [
            (d or "").strip().lstrip(".").lower()
            for d in (info or {}).get("domains", [])
            if d
        ]
        if domains:
            site_domains[slug] = list(dict.fromkeys(domains))

    if not site_domains:
        raise CookieCloudSyncError("未找到可同步的站点域名配置")

    flattened: list[Dict[str, Any]] = []
    for host, entries in (cookie_data or {}).items():
        if not isinstance(entries, list):
            continue
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            normalized = dict(entry)
            if not normalized.get("domain"):
                normalized["domain"] = host
            flattened.append(normalized)

    get_site_cookies_dir().mkdir(parents=True, exist_ok=True)

    result_sites: Dict[str, Dict[str, Any]] = {}
    skipped_sites: Dict[str, Dict[str, Any]] = {}
    for slug, domains in site_domains.items():
        matched: Dict[tuple[str, str, str], Dict[str, Any]] = {}
        for cookie in flattened:
            raw_domain = cookie.get("domain")
            cookie_domain = _normalize_domain(raw_domain)
            if not cookie_domain:
                continue

            if not any(_domain_matches(cookie_domain, d) for d in domains):
                continue

            name = str(cookie.get("name") or "").strip()
            path = str(cookie.get("path") or "/")
            if not name:
                continue

            key = (cookie_domain, path, name)
            existing = matched.get(key)
            if existing is None:
                matched[key] = cookie
                continue

            existing_exp = _to_int_seconds(existing.get("expirationDate"))
            new_exp = _to_int_seconds(cookie.get("expirationDate"))
            if new_exp > existing_exp:
                matched[key] = cookie

        if not matched:
            continue

        lines = ["# Netscape HTTP Cookie File"]
        for cookie in matched.values():
            line = _cookie_to_netscape_line(cookie)
            if line:
                lines.append(line)

        path = get_site_cookies_file_path(slug)
        validation_error = _validate_cookie_lines_for_site(slug, lines)
        if validation_error:
            logger.warning(
                '[CookieCloudSync] Skip replacing %s cookies because validation failed: %s',
                slug,
                validation_error,
            )
            skipped_sites[slug] = {
                'cookies': max(0, len(lines) - 1),
                'path': str(path),
                'reason': validation_error,
            }
            continue

        write_cookie_text_file(path, '\n'.join(lines) + '\n')
        result_sites[slug] = {
            "cookies": max(0, len(lines) - 1),
            "path": str(path),
        }

    synced_at = datetime.now(timezone.utc).isoformat()
    return {
        "synced_at": synced_at,
        "total_cookie_entries": len(flattened),
        "updated_sites": len(result_sites),
        "sites": result_sites,
        "skipped_sites": skipped_sites,
    }
