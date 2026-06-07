from __future__ import annotations

import html as html_lib
import http.cookiejar as cookielib
import logging
import re
import time
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


def _extract_top_level_domain_from_url(target_url: str) -> str:
    netloc = urlparse(target_url).netloc
    # strip port
    host = netloc.split(':', 1)[0]
    parts = [p for p in host.split('.') if p]
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return host


CookieFileResolver = Callable[[str], str | None]
CookieDomainResolver = Callable[[str], str]

_cookie_file_resolver: CookieFileResolver | None = None
_cookie_domain_resolver: CookieDomainResolver | None = None


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
        except (TypeError, ValueError):
            resolved = ''
        if resolved:
            return resolved
    return str(_extract_top_level_domain_from_url(target_url) or '').strip().lower()


def _resolve_cookie_file(target_url: str, cookies_file: str | None) -> Path | None:
    if cookies_file:
        try:
            return Path(cookies_file).expanduser()
        except (OSError, RuntimeError):
            return None

    if _cookie_file_resolver is None:
        return None

    try:
        resolved_path = _cookie_file_resolver(target_url)
    except (TypeError, ValueError):
        return None

    if not resolved_path:
        return None

    try:
        return Path(resolved_path).expanduser()
    except (OSError, RuntimeError):
        return None


def resolve_cookie_file_path(target_url: str, cookies_file: str | None = None) -> str | None:
    """Return the cookie file path if available for the given URL.

    This leverages either a user-provided ``cookies_file`` argument or the
    resolver configured via :func:`configure_cookie_file_resolver`.
    """

    cookie_path = _resolve_cookie_file(target_url, cookies_file)
    if not cookie_path or not cookie_path.is_file():
        return None
    return str(cookie_path)


def filter_cookies_to_query_string(target_url: str, cookies_file: str | None = None) -> str:
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
    except (OSError, ValueError):
        return ""

    domain = _extract_cookie_domain(target_url)
    filtered_cj = cookielib.CookieJar()

    for cookie in jar:
        try:
            if cookie.domain.endswith(domain):
                filtered_cj.set_cookie(cookie)
        except (AttributeError, TypeError):
            continue

    cookie_strings = [f"{cookie.name}={cookie.value}" for cookie in filtered_cj]
    return "; ".join(cookie_strings)


# ---------------------------------------------------------------------------
# Shared thumbnail helpers (extracted from duplicate site-runtime extractors)
# ---------------------------------------------------------------------------

META_THUMBNAIL_PATTERNS = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.I),
)

PAGE_FETCH_MAX_ATTEMPTS = 3
PAGE_FETCH_RETRYABLE_STATUS_CODES = {403, 408, 425, 429, 500, 502, 503, 504}


def looks_like_expiring_preview_thumbnail(url: str, prefix: str = '/plain/') -> bool:
    normalized = str(url or '').strip().lower()
    return bool(normalized) and prefix in normalized and (
        'validto=' in normalized or 'hdnea=' in normalized
    )


def _thumbnail_expiry_score(url: str) -> float:
    normalized = str(url or '').strip().lower()
    if not normalized:
        return -1
    if not any(token in normalized for token in ('validto=', 'hdnea=', 'hmac=', 'hash=')):
        return float('inf')

    validto_match = re.search(r'[?&]validto=(\d+)', normalized)
    if validto_match:
        return float(validto_match.group(1))

    hdnea_exp_match = re.search(r'(?:^|[~&])exp=(\d+)', normalized)
    if hdnea_exp_match:
        return float(hdnea_exp_match.group(1))

    return 0


def pick_best_thumbnail_url(thumbnail_urls: list[str]) -> str | None:
    unique_urls = []
    for thumbnail_url in thumbnail_urls:
        normalized = html_lib.unescape(str(thumbnail_url or '').strip())
        if normalized and normalized not in unique_urls:
            unique_urls.append(normalized)

    if not unique_urls:
        return None

    return max(unique_urls, key=_thumbnail_expiry_score)


def normalize_thumbnail(
    video_info: dict,
    source_url: str | None,
    fetch_fn,
) -> None:
    """Normalize thumbnail URL — replace expiring preview thumbnails with a fresh page-sourced one.

    ``fetch_fn(url)`` is called to obtain a replacement thumbnail URL from the video page.
    """
    thumbnail_url = str(video_info.get('thumbnail') or '').strip()
    if not looks_like_expiring_preview_thumbnail(thumbnail_url):
        return

    page_url = source_url or str(video_info.get('webpage_url') or '').strip()
    if not page_url:
        return

    fresh_thumbnail_url = fetch_fn(page_url)
    if not fresh_thumbnail_url:
        return

    video_info['thumbnail'] = fresh_thumbnail_url
    if isinstance(video_info.get('thumbnails'), list) and video_info['thumbnails']:
        video_info['thumbnails'][0]['url'] = fresh_thumbnail_url


def build_cookie_header(url: str, age_gate_cookies: dict[str, str]) -> str:
    """Build a Cookie header string from cookie file plus age-gate defaults."""
    cookies: dict[str, str] = {}
    raw_cookie_header = filter_cookies_to_query_string(url)

    for segment in raw_cookie_header.split(';'):
        item = segment.strip()
        if not item or '=' not in item:
            continue
        name, value = item.split('=', 1)
        cookies[name.strip()] = value.strip()

    for name, value in age_gate_cookies.items():
        cookies.setdefault(name, value)

    return '; '.join(f'{name}={value}' for name, value in cookies.items())


def fetch_page_thumbnail_url(
    url: str,
    cookie_file: str | None,
    build_headers_fn,
) -> str | None:
    """Fetch a video page and extract the best og:image / twitter:image URL.

    ``build_headers_fn(url, cookie_file)`` produces request headers.
    Uses ``httpx`` with retry support.
    """
    import httpx

    page_url = str(url or '').strip()
    if not page_url:
        return None

    headers = build_headers_fn(page_url, cookie_file)

    for attempt in range(1, PAGE_FETCH_MAX_ATTEMPTS + 1):
        try:
            response = httpx.get(
                page_url,
                headers=headers,
                follow_redirects=True,
                timeout=30.0,
            )
        except Exception as exc:
            logger.warning('Failed to fetch page thumbnail metadata: %s', exc)
            return None

        if response.status_code == 200:
            thumbnail_urls = []
            for pattern in META_THUMBNAIL_PATTERNS:
                for match in pattern.finditer(response.text):
                    thumbnail_url = html_lib.unescape(match.group(1).strip())
                    if thumbnail_url:
                        thumbnail_urls.append(thumbnail_url)
            return pick_best_thumbnail_url(thumbnail_urls)

        if (
            response.status_code in PAGE_FETCH_RETRYABLE_STATUS_CODES
            and attempt < PAGE_FETCH_MAX_ATTEMPTS
        ):
            time.sleep(min(5.0, 0.8 * attempt))
            continue

        return None

    return None


