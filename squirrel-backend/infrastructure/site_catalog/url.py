import ipaddress
import logging
import time
from urllib.parse import urlparse

from infrastructure.site_plugins.registry import get_site_plugin_registry

logger = logging.getLogger(__name__)

_SITE_REGISTRATION_INDEX_TTL = 30.0
_DOMAIN_SITE_CACHE_TTL = 300.0
_site_registration_index: dict[str, str] = {}
_site_registration_index_cached_at = 0.0
_domain_site_cache: dict[str, tuple[str | None, float]] = {}


def extract_top_level_domain(url):
    """Extract top-level domain from URL (including second level if exists, e.g., example.com).

    :param url: Full URL string
    :return: Top-level domain string
    """
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')

    if len(domain_parts) == 2:
        return parsed_url.netloc
    return '.'.join(domain_parts[-2:])


def extract_second_level_domain(domain_or_url: str) -> str:
    """Extract second level domain from URL or domain string"""
    if not domain_or_url:
        return domain_or_url

    if '://' in domain_or_url:
        parsed = urlparse(domain_or_url)
        domain = parsed.hostname or domain_or_url
    else:
        domain = domain_or_url

    # Split domain parts
    parts = domain.lower().split('.')

    # Return last two parts for second level domain
    if len(parts) >= 2:
        return '.'.join(parts[-2:])

    return domain


def normalize_domain(domain_or_url: str) -> str | None:
    """Normalize a URL or domain to a lower-cased second-level domain."""
    if not domain_or_url:
        return domain_or_url

    value = domain_or_url.strip().lower()
    if not value:
        return value

    if '://' not in value:
        value = f'http://{value}'

    parsed = urlparse(value)
    hostname = parsed.hostname or domain_or_url
    hostname = hostname.split(':')[0].lower()

    try:
        ipaddress.ip_address(hostname)
        return hostname
    except ValueError:
        pass

    parts = hostname.split('.')
    if len(parts) >= 2:
        return '.'.join(parts[-2:])

    return hostname


def _normalize_registration_domain(domain: str) -> str:
    value = str(domain or '').strip().lower()
    if not value:
        return ''
    return value.lstrip('.')


def _build_site_registration_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for site_name, info in get_site_plugin_registry().build_site_catalog().items():
        for candidate in info.get('domains') or []:
            normalized = _normalize_registration_domain(candidate)
            if normalized:
                index.setdefault(normalized, site_name)
    return index


def _get_site_registration_index() -> dict[str, str]:
    global _site_registration_index, _site_registration_index_cached_at

    now = time.time()
    if _site_registration_index and now - _site_registration_index_cached_at <= _SITE_REGISTRATION_INDEX_TTL:
        return _site_registration_index

    _site_registration_index = _build_site_registration_index()
    _site_registration_index_cached_at = now
    return _site_registration_index


def _resolve_site_from_domain(domain: str) -> str | None:
    now = time.time()
    cached = _domain_site_cache.get(domain)
    if cached is not None:
        site_name, cached_at = cached
        if now - cached_at <= _DOMAIN_SITE_CACHE_TTL:
            return site_name

    index = _get_site_registration_index()
    parts = domain.split('.')
    site_name = None
    for start in range(len(parts)):
        candidate = '.'.join(parts[start:])
        if candidate in index:
            site_name = index[candidate]
            break

    _domain_site_cache[domain] = (site_name, now)
    return site_name


def resolve_site(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return extract_top_level_domain(url)
    except (ValueError, TypeError):
        return None


def reset_site_lookup_cache() -> None:
    _domain_site_cache.clear()
    global _site_registration_index, _site_registration_index_cached_at
    _site_registration_index = {}
    _site_registration_index_cached_at = 0.0


def get_site_from_url(url: str) -> str | None:
    """Get site name from URL using plugin domains.

    :param url: Full URL string
    :return: Site name, or None if not found
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
        domain = (parsed.hostname or '').lower()
        if not domain:
            return None

        return _resolve_site_from_domain(domain)
    except (ValueError, AttributeError, TypeError) as e:
        logger.error('get_site_from_url exception occurred: url=%s, error=%s', url, e, exc_info=True)
        return None
