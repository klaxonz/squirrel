from __future__ import annotations

import urllib.parse

from ._base import RssAccountConfig, RssServiceError
from ._fever import FeverClient
from ._greader import GReaderClient
from ._miniflux import MinifluxClient

SUPPORTED_PROVIDERS = {'greader', 'miniflux', 'fever'}
DEFAULT_SYNC_ENTRY_LIMIT = 100
MAX_SYNC_ENTRY_LIMIT = 5000
PROVIDER_CAPABILITIES = {
    'greader': {'manage_subscriptions': True},
    'miniflux': {'manage_subscriptions': True},
    'fever': {'manage_subscriptions': False},
}


def create_client(config: RssAccountConfig) -> MinifluxClient | FeverClient | GReaderClient:
    if config.provider == 'greader':
        return GReaderClient(config)
    if config.provider == 'miniflux':
        return MinifluxClient(config)
    if config.provider == 'fever':
        return FeverClient(config)
    raise RssServiceError(f'Unsupported RSS provider: {config.provider}')


def normalize_provider(provider: str) -> str:
    normalized = str(provider or '').strip().lower()
    if normalized not in SUPPORTED_PROVIDERS:
        raise RssServiceError(f'Unsupported RSS provider: {provider}')
    return normalized


def get_provider_capabilities(provider: str) -> dict[str, bool]:
    return dict(PROVIDER_CAPABILITIES[normalize_provider(provider)])


def normalize_base_url(base_url: str) -> str:
    normalized = str(base_url or '').strip().rstrip('/')
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise RssServiceError('RSS service URL must be an HTTP or HTTPS URL')
    return normalized


def normalize_sync_entry_limit(provider: str, sync_entry_limit: int | None) -> int | None:
    if sync_entry_limit is None:
        if provider == 'greader':
            return None
        return DEFAULT_SYNC_ENTRY_LIMIT
    try:
        limit = int(sync_entry_limit)
    except (TypeError, ValueError) as exc:
        raise RssServiceError('Sync entry limit must be an integer') from exc
    if limit < 1:
        raise RssServiceError('Sync entry limit must be greater than 0')
    if limit > MAX_SYNC_ENTRY_LIMIT:
        raise RssServiceError(f'Sync entry limit must not exceed {MAX_SYNC_ENTRY_LIMIT}')
    return limit
