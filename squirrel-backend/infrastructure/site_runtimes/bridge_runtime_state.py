from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from crawl import (
    configure_cookie_domain_resolver,
    configure_cookie_file_resolver,
    configure_rate_limit,
    configure_rate_limit_enabled,
)

from infrastructure.site_catalog.cookie_files import get_site_cookies_file_path


def _parse_bool(value, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {'true', '1', 'yes', 'y', 'on'}:
        return True
    if text in {'false', '0', 'no', 'n', 'off'}:
        return False
    return default


def _extract_host(target_url: str) -> str:
    parsed = urlparse(target_url)
    return (parsed.hostname or '').split(':', 1)[0].lstrip('.').lower()


def _extract_top_level_domain(target_url: str) -> str:
    host = _extract_host(target_url)
    parts = [part for part in host.split('.') if part]
    if len(parts) >= 2:
        return '.'.join(parts[-2:])
    return host


def _runtime_cookie_entries(site_configs: dict[str, dict]) -> list[dict]:
    entries = []
    for site_name, config in site_configs.items():
        cookie_config = dict(config.get('cookie') or {})
        domains = [str(domain or '').strip().lstrip('.').lower() for domain in config.get('domains', []) if domain]
        aliases = [
            str(domain or '').strip().lstrip('.').lower()
            for domain in cookie_config.get('alias_domains', [])
            if domain
        ]
        match_domain = str(cookie_config.get('match_domain') or '').strip().lstrip('.').lower()
        entries.append({
            'site_name': site_name,
            'domains': domains,
            'aliases': aliases,
            'match_domain': match_domain,
        })
    return entries


def _matches_host(host: str, domain: str) -> bool:
    return bool(domain and (host == domain or host.endswith(f'.{domain}')))


def _configure_runtime_cookie_resolver(site_configs: dict[str, dict]) -> None:
    entries = _runtime_cookie_entries(site_configs)

    def resolve_cookie_file(target_url: str) -> str | None:
        host = _extract_host(target_url)
        for entry in entries:
            if any(_matches_host(host, domain) for domain in entry['domains']):
                path = get_site_cookies_file_path(entry['site_name'])
                return str(path) if Path(path).exists() else None
            if any(_matches_host(host, alias) for alias in entry['aliases']):
                path = get_site_cookies_file_path(entry['site_name'])
                return str(path) if Path(path).exists() else None
        return None

    def resolve_cookie_domain(target_url: str) -> str:
        host = _extract_host(target_url)
        for entry in entries:
            if entry['match_domain'] and any(_matches_host(host, alias) for alias in entry['aliases']):
                return entry['match_domain']
        return _extract_top_level_domain(target_url)

    configure_cookie_file_resolver(resolve_cookie_file)
    configure_cookie_domain_resolver(resolve_cookie_domain)


def _configure_runtime_rate_limits(site_configs: dict[str, dict]) -> None:
    for config in site_configs.values():
        rate_limit = dict(config.get('rate_limit') or {})
        enabled = _parse_bool(rate_limit.get('enabled'), True)
        min_interval = rate_limit.get('min_interval')
        max_interval = rate_limit.get('max_interval')
        for domain in config.get('domains', []):
            if not domain:
                continue
            configure_rate_limit_enabled(domain, enabled)
            if not enabled or min_interval in (None, '') or max_interval in (None, ''):
                continue
            configure_rate_limit(domain, float(min_interval), float(max_interval))


def configure_backend_runtime_state(site_configs: dict[str, dict]) -> None:
    try:
        from infrastructure.site_catalog.cloudflare_bypass import get_default_client
        from infrastructure.site_catalog.runtime_http import set_cloudflare_bypass_client

        set_cloudflare_bypass_client(get_default_client())
    except Exception:
        # process boundary -- optional runtime init, must not crash the subprocess
        pass

    _configure_runtime_cookie_resolver(site_configs)
    _configure_runtime_rate_limits(site_configs)
