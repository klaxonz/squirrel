import http.cookiejar as cookielib
from pathlib import Path
from urllib.parse import urlparse

from infrastructure.config.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.cookie_files import get_site_cookies_file_path


def _get_cookie_site_catalog() -> dict:
    return get_effective_site_catalog()


def _extract_host_from_url(target_url: str) -> str | None:
    if not target_url:
        return None
    parsed = urlparse(target_url)
    host = parsed.hostname or ""
    if not host:
        return None
    return host.split(":", 1)[0].lstrip(".").lower()


def _iter_cookie_alias_matches(host: str):
    normalized_host = str(host or "").strip().lower()
    if not normalized_host:
        return

    catalog = _get_cookie_site_catalog()

    for slug, entry in catalog.items():
        cookie_config = entry.get("cookie") or {}
        alias_domains = cookie_config.get("alias_domains") or []
        match_domain = str(cookie_config.get("match_domain") or "").strip().lower() or None
        for alias_domain in alias_domains:
            normalized_alias = str(alias_domain or "").strip().lstrip(".").lower()
            if not normalized_alias:
                continue
            if normalized_host == normalized_alias or normalized_host.endswith(f".{normalized_alias}"):
                yield slug, match_domain


def resolve_cookie_file_for_url(target_url: str) -> str | None:
    host = _extract_host_from_url(target_url)
    if not host:
        return None

    catalog = _get_cookie_site_catalog()

    matched_site: str | None = None
    for slug, entry in catalog.items():
        try:
            domains = [(d or "").strip().lstrip(".").lower() for d in entry.get("domains", []) if d]
        except (KeyError, AttributeError, TypeError):
            continue
        for d in domains:
            if host == d or host.endswith("." + d):
                matched_site = slug
                break
        if matched_site:
            break

    if not matched_site:
        matched_site = next((slug for slug, _match_domain in _iter_cookie_alias_matches(host)), None)

    if not matched_site:
        return None

    path = get_site_cookies_file_path(matched_site)
    if not path.exists():
        return None

    return str(path)


def _extract_top_level_domain_from_url(target_url: str) -> str:
    host = _extract_host_from_url(target_url) or ""
    parts = [part for part in host.split(".") if part]
    if len(parts) >= 2:
        return ".".join(parts[-2:])
    return host


def resolve_cookie_match_domain_for_url(target_url: str) -> str:
    host = _extract_host_from_url(target_url) or ""
    for _slug, match_domain in _iter_cookie_alias_matches(host):
        if match_domain:
            return match_domain
    return _extract_top_level_domain_from_url(target_url)


def _read_cookie_file_as_query_string(path: str | None, target_url: str) -> str:
    if not path:
        return ""

    try:
        cookie_path = Path(path).expanduser()
    except (OSError, RuntimeError):
        return ""

    if not cookie_path.is_file():
        return ""

    domain = resolve_cookie_match_domain_for_url(target_url)
    if not domain:
        return ""

    jar = cookielib.MozillaCookieJar()

    try:
        jar.load(str(cookie_path), ignore_discard=True, ignore_expires=True)
    except (OSError, ValueError):
        return ""

    filtered = []
    for item in jar:
        try:
            if item.domain.endswith(domain):
                filtered.append(f"{item.name}={item.value}")
        except (AttributeError, TypeError):
            continue

    header_value = "; ".join(filtered)
    return header_value


def filter_cookies_to_query_string(target_url: str) -> str:
    cookie_file = resolve_cookie_file_for_url(target_url)
    return _read_cookie_file_as_query_string(cookie_file, target_url)
