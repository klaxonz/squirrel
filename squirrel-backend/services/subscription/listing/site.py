from __future__ import annotations

from urllib.parse import urlparse

from services.site_catalog.catalog import SiteCatalog
from utils.url_helper import extract_top_level_domain, get_site_from_url


def resolve_subscription_nsfw(url: str) -> bool:
    _slug, info = SiteCatalog.find_site_by_domain(extract_top_level_domain(url))
    if not info:
        return False
    metadata = info.get('metadata', {})
    return bool(metadata.get('nsfw', False))


def resolve_site_slug(url: str | None) -> str | None:
    if not url:
        return None
    try:
        slug = get_site_from_url(url)
        if slug:
            return slug

        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path.split('/')[0]
        slug, _info = SiteCatalog.find_site_by_domain(domain)
        return slug
    except (ValueError, TypeError):
        return None
