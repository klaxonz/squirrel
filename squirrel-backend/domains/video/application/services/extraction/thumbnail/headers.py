import time
from urllib.parse import urlparse

from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.site_catalog.cookies import filter_cookies_to_query_string
from infrastructure.site_catalog.site_constants import (
    SITE_META_OFFLINE_THUMBNAILS_DISPLAY,
    SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD,
)

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
}

EFFECTIVE_CATALOG_CACHE_TTL = 10.0

SITE_COOKIE_DEFAULTS: dict[str, dict[str, str]] = {
    'pornhub': {
        'age_verified': '1',
        'accessAgeDisclaimerPH': '1',
        'accessAgeDisclaimerUK': '1',
        'accessPH': '1',
    },
}


class ThumbnailSiteConfig:
    """Cached site configuration used by thumbnail fetches."""

    def __init__(self) -> None:
        self._effective_catalog: dict | None = None
        self._effective_catalog_cached_at = 0.0

    def get_effective_catalog(self) -> dict:
        now = time.time()
        if self._effective_catalog is None or now - self._effective_catalog_cached_at > EFFECTIVE_CATALOG_CACHE_TTL:
            self._effective_catalog = get_effective_site_catalog()
            self._effective_catalog_cached_at = now
        return self._effective_catalog

    def site_info(self, site_name: str | None) -> dict:
        if not site_name:
            return {}
        return self.get_effective_catalog().get(site_name.lower(), {})

    def should_download(self, site_name: str) -> bool:
        site_info = self.site_info(site_name)
        metadata = site_info.get('metadata', {})
        return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD, False)

    def should_use_offline(self, site_name: str) -> bool:
        site_info = self.site_info(site_name)
        metadata = site_info.get('metadata', {})
        return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DISPLAY, False)

    def site_requires_cookies(self, site_name: str | None) -> bool:
        metadata = self.site_info(site_name).get('metadata') or {}
        return bool(metadata.get('requires_cookies'))


def parse_cookie_header(cookie_header: str | None) -> dict[str, str]:
    cookies: dict[str, str] = {}
    for segment in str(cookie_header or '').split(';'):
        item = segment.strip()
        if not item or '=' not in item:
            continue
        name, value = item.split('=', 1)
        clean_name = name.strip()
        if clean_name:
            cookies[clean_name] = value.strip()
    return cookies


def build_request_headers(
    site_config: ThumbnailSiteConfig,
    site_name: str | None,
    *,
    source_url: str | None = None,
    target_url: str | None = None,
) -> dict[str, str]:
    headers = dict(DEFAULT_HEADERS)
    if not site_name:
        return headers

    site_info = site_config.site_info(site_name)
    http_headers = (site_info.get('http') or {}).get('headers') or {}
    for key, value in http_headers.items():
        if value is not None:
            headers[str(key)] = str(value)

    effective_referer = str(source_url or headers.get('Referer') or '').strip()
    if effective_referer:
        headers['Referer'] = effective_referer

    referer = headers.get('Referer')
    if referer and 'Origin' not in headers:
        parsed = urlparse(referer)
        if parsed.scheme and parsed.netloc:
            headers['Origin'] = f'{parsed.scheme}://{parsed.netloc}'

    if site_config.site_requires_cookies(site_name):
        cookies = parse_cookie_header(headers.get('Cookie'))
        cookie_lookup_url = source_url or target_url
        if cookie_lookup_url:
            cookies.update(parse_cookie_header(filter_cookies_to_query_string(cookie_lookup_url)))

        for name, value in SITE_COOKIE_DEFAULTS.get(str(site_name).lower(), {}).items():
            cookies.setdefault(name, value)

        if cookies:
            headers['Cookie'] = '; '.join(f'{name}={value}' for name, value in cookies.items())

    return headers

