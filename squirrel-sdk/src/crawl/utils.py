from __future__ import annotations

import http.cookiejar as cookielib
import os
from typing import Optional
from urllib.parse import urlparse


def _extract_top_level_domain_from_url(target_url: str) -> str:
    netloc = urlparse(target_url).netloc
    # strip port
    host = netloc.split(':', 1)[0]
    parts = [p for p in host.split('.') if p]
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return host


def filter_cookies_to_query_string(target_url: str, cookies_file: Optional[str] = None) -> str:
    """Read a Netscape cookie file and return cookies for target domain as a header string.

    The cookie file path is taken from the `SQUIRREL_COOKIES_FILE` environment
    variable if not explicitly provided.
    """
    file_path = cookies_file or os.environ.get("SQUIRREL_COOKIES_FILE")
    if not file_path or not os.path.exists(file_path):
        return ""

    cj = cookielib.MozillaCookieJar()
    try:
        cj.load(file_path, ignore_discard=True, ignore_expires=True)
    except Exception:
        return ""

    domain = _extract_top_level_domain_from_url(target_url)
    filtered_cj = cookielib.CookieJar()

    for cookie in cj:
        try:
            if cookie.domain.endswith(domain):
                filtered_cj.set_cookie(cookie)
        except Exception:
            continue

    cookie_strings = [f"{cookie.name}={cookie.value}" for cookie in filtered_cj]
    return "; ".join(cookie_strings)


