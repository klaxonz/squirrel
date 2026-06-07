from __future__ import annotations

from typing import Optional
import urllib.parse

from ._base import RssAccountConfig, RssServiceError
from ._miniflux import MinifluxClient
from ._fever import FeverClient
from ._greader import GReaderClient

SUPPORTED_PROVIDERS = {'greader', 'miniflux', 'fever'}


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


def normalize_base_url(base_url: str) -> str:
    normalized = str(base_url or '').strip().rstrip('/')
    parsed = urllib.parse.urlparse(normalized)
    if parsed.scheme not in {'http', 'https'} or not parsed.netloc:
        raise RssServiceError('RSS service URL must be an HTTP or HTTPS URL')
    return normalized


def normalize_sync_entry_limit(provider: str, sync_entry_limit: Optional[int]) -> Optional[int]:
    if sync_entry_limit is None:
        if provider == 'greader':
            return None
        raise RssServiceError('Sync entry limit is required for this RSS provider')
    limit = int(sync_entry_limit)
    if limit < 1:
        raise RssServiceError('Sync entry limit must be greater than 0')
    return limit
