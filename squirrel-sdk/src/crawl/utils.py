from __future__ import annotations

import http.cookiejar as cookielib
from pathlib import Path
from typing import Callable, Optional
from urllib.parse import urlparse


def _extract_top_level_domain_from_url(target_url: str) -> str:
    netloc = urlparse(target_url).netloc
    # strip port
    host = netloc.split(':', 1)[0]
    parts = [p for p in host.split('.') if p]
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return host


CookieFileResolver = Callable[[str], Optional[str]]
CookieDomainResolver = Callable[[str], str]

_cookie_file_resolver: Optional[CookieFileResolver] = None
_cookie_domain_resolver: Optional[CookieDomainResolver] = None


def configure_cookie_file_resolver(resolver: CookieFileResolver) -> None:
    """Register a callback used to resolve cookie files at runtime.

    Legacy compatibility only: host runtimes should prefer owning cookie file
    resolution locally instead of mutating SDK-global resolver state.
    """

    global _cookie_file_resolver
    _cookie_file_resolver = resolver


def configure_cookie_domain_resolver(resolver: CookieDomainResolver) -> None:
    """Register a callback used to resolve cookie matching domains at runtime."""

    global _cookie_domain_resolver
    _cookie_domain_resolver = resolver


def _extract_cookie_domain(target_url: str) -> str:
    if _cookie_domain_resolver is not None:
        try:
            resolved = str(_cookie_domain_resolver(target_url) or '').strip().lower()
        except Exception:
            resolved = ''
        if resolved:
            return resolved
    return str(_extract_top_level_domain_from_url(target_url) or '').strip().lower()


def _resolve_cookie_file(target_url: str, cookies_file: Optional[str]) -> Optional[Path]:
    if cookies_file:
        try:
            return Path(cookies_file).expanduser()
        except Exception:
            return None

    if _cookie_file_resolver is None:
        return None

    try:
        resolved_path = _cookie_file_resolver(target_url)
    except Exception:
        return None

    if not resolved_path:
        return None

    try:
        return Path(resolved_path).expanduser()
    except Exception:
        return None


def resolve_cookie_file_path(target_url: str, cookies_file: Optional[str] = None) -> Optional[str]:
    """Return the cookie file path if available for the given URL.

    This leverages either a user-provided ``cookies_file`` argument or the
    resolver configured via :func:`configure_cookie_file_resolver`.
    """

    cookie_path = _resolve_cookie_file(target_url, cookies_file)
    if not cookie_path or not cookie_path.is_file():
        return None
    return str(cookie_path)


def filter_cookies_to_query_string(target_url: str, cookies_file: Optional[str] = None) -> str:
    """Read a Netscape cookie file and return cookies for target domain as a header string.

    The caller is responsible for providing the cookie file path, either directly
    or via :func:`configure_cookie_file_resolver`.
    """
    cookie_path = _resolve_cookie_file(target_url, cookies_file)

    if not cookie_path or not cookie_path.is_file():
        return ""

    jar = cookielib.MozillaCookieJar()

    try:
        jar.load(str(cookie_path), ignore_discard=True, ignore_expires=True)
    except Exception:
        return ""

    domain = _extract_cookie_domain(target_url)
    filtered_cj = cookielib.CookieJar()

    for cookie in jar:
        try:
            if cookie.domain.endswith(domain):
                filtered_cj.set_cookie(cookie)
        except Exception:
            continue

    cookie_strings = [f"{cookie.name}={cookie.value}" for cookie in filtered_cj]
    return "; ".join(cookie_strings)


