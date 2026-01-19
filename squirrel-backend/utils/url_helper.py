from typing import Optional
from urllib.parse import urlparse
import logging
import ipaddress


logger = logging.getLogger(__name__)


def extract_top_level_domain(url):
    """
    Extract top-level domain from URL (including second level if exists, e.g., example.com).

    :param url: Full URL string
    :return: Top-level domain string
    """
    parsed_url = urlparse(url)
    domain_parts = parsed_url.netloc.split('.')

    if len(domain_parts) == 2:
        return parsed_url.netloc
    else:
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


def normalize_domain(domain_or_url: str) -> Optional[str]:
    """Normalize a URL or domain to a lower-cased second-level domain."""
    if not domain_or_url:
        return domain_or_url

    value = domain_or_url.strip().lower()
    if not value:
        return value

    if '://' not in value:
        value = f"http://{value}"

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



def get_site_from_url(url: str) -> Optional[str]:
    """
    Get site name from URL using registered extractor mapping

    :param url: Full URL string
    :return: Site name, or None if not found
    """
    if not url:
        return None
    try:
        from core.extraction.factory import get_extractor_registry

        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        registry = get_extractor_registry()
        site_name = registry.get_by_domain(domain)

        if not site_name and domain.startswith('www.'):
            domain = domain[4:]
            site_name = registry.get_by_domain(domain)

        return site_name
    except Exception as e:
        logger.error(f"get_site_from_url exception occurred: url={url}, error={str(e)}", exc_info=True)
        return None
