import logging
import json
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urljoin, urlparse

import requests

from core.config import settings
from core.cookie_config import get_site_cookies_dir, get_site_cookies_file_path, write_cookie_text_file
from core.site_config_manager import get_effective_site_catalog

logger = logging.getLogger(__name__)


class CookieCloudSyncError(RuntimeError):
    pass


def _get_cookiecloud_config() -> Tuple[str, str, str]:
    url = (settings.COOKIECLOUD_URL or "").strip()
    uuid = (settings.COOKIECLOUD_UUID or "").strip()
    password = (settings.COOKIECLOUD_PASSWORD or "").strip()
    return url, uuid, password


def is_cookiecloud_configured() -> bool:
    url, uuid, password = _get_cookiecloud_config()
    return bool(url and uuid and password)


def _decode_cookiecloud_response_json(response: requests.Response) -> Dict[str, Any]:
    payload = response.content or b''
    attempted_encodings: list[str] = []
    last_error: Exception | None = None

    encodings = [
        response.encoding,
        getattr(response, 'apparent_encoding', None),
        'utf-8',
        'utf-8-sig',
        'latin-1',
    ]

    for encoding in encodings:
        if not encoding or encoding in attempted_encodings:
            continue
        attempted_encodings.append(encoding)
        try:
            return json.loads(payload.decode(encoding))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            last_error = exc

    raise CookieCloudSyncError(
        'CookieCloud 响应不是有效的 JSON 数据，请检查服务端编码或反向代理压缩配置'
    ) from last_error


def _fetch_cookiecloud_encrypted_data(url: str, uuid: str) -> str:
    api_root = urlparse(url).path or '/'
    request_path = str(PurePosixPath(api_root, 'get', uuid))

    try:
        response = requests.get(urljoin(url, request_path), timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise CookieCloudSyncError(f'CookieCloud 请求失败: {exc}') from exc

    payload = _decode_cookiecloud_response_json(response)
    encrypted_data = payload.get('encrypted')
    if not isinstance(encrypted_data, str) or not encrypted_data.strip():
        raise CookieCloudSyncError('CookieCloud 响应缺少 encrypted 字段')
    return encrypted_data


def fetch_cookiecloud_cookie_data() -> Dict[str, Any]:
    url, uuid, password = _get_cookiecloud_config()
    if not url or not uuid or not password:
        raise CookieCloudSyncError(
            "CookieCloud 未配置，请设置 COOKIECLOUD_URL / COOKIECLOUD_UUID / COOKIECLOUD_PASSWORD"
        )

    try:
        from PyCookieCloud import PyCookieCloud
        from PyCookieCloud.PyCryptoJS import decrypt
    except ImportError as exc:
        raise CookieCloudSyncError(f"缺少依赖 PyCookieCloud: {exc}") from exc

    client = PyCookieCloud(url=url, uuid=uuid, password=password)
    encrypted_data = _fetch_cookiecloud_encrypted_data(url=url, uuid=uuid)
    try:
        decrypted_data = decrypt(encrypted_data, client.get_the_key().encode('utf-8')).decode('utf-8')
        payload = json.loads(decrypted_data)
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise CookieCloudSyncError(f'CookieCloud 解密失败: {exc}') from exc

    data = payload.get('cookie_data')
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
    except (TypeError, ValueError):
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
    }
