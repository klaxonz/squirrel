import logging
import os

from services.video.extraction.thumbnail.client import ThumbnailHttpClient
from services.video.extraction.thumbnail.headers import ThumbnailSiteConfig, build_request_headers
from services.video.extraction.thumbnail.html import looks_like_expiring_preview_thumbnail
from services.video.extraction.thumbnail.local_index import ThumbnailLocalIndexRepository
from services.video.extraction.thumbnail.storage import ThumbnailStorage
from utils.url_helper import get_site_from_url

logger = logging.getLogger(__name__)

EXPIRING_PREVIEW_REFRESH_STATUS_CODES = {403, 404, 410, 472}


class ThumbnailDownloaderService:
    """Coordinates thumbnail lookup, download, and local cache indexing."""

    def __init__(
        self,
        site_config: ThumbnailSiteConfig | None = None,
        storage: ThumbnailStorage | None = None,
        local_index: ThumbnailLocalIndexRepository | None = None,
        http_client: ThumbnailHttpClient | None = None,
    ) -> None:
        self._site_config = site_config or ThumbnailSiteConfig()
        self._storage = storage or ThumbnailStorage()
        self._local_index = local_index or ThumbnailLocalIndexRepository(self._storage)
        self._http_client = http_client or ThumbnailHttpClient()

    def close(self) -> None:
        self._http_client.close()

    def build_request_headers(
        self,
        site_name: str | None,
        *,
        source_url: str | None = None,
        target_url: str | None = None,
    ) -> dict[str, str]:
        return build_request_headers(
            self._site_config,
            site_name,
            source_url=source_url,
            target_url=target_url,
        )

    def download_thumbnail(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str | None = None,
        source_url: str | None = None,
    ) -> str | None:
        """Download thumbnail to local storage."""
        if not thumbnail_url:
            return None

        if site_name and not self._site_config.should_download(site_name):
            logger.debug('Thumbnail download disabled for site: %s', site_name)
            return None

        batch_dir, batch_name, file_path = self._storage.target_file_path(video_id, thumbnail_url)
        if os.path.exists(file_path):
            logger.debug('Thumbnail already exists: %s', file_path)
            self._local_index.upsert(video_id, batch_name, os.path.basename(file_path), exists=True)
            return file_path

        response = self._request_thumbnail(video_id, thumbnail_url, site_name, source_url)
        if response is None:
            return None

        if response.status_code != 200 and response.status_code in EXPIRING_PREVIEW_REFRESH_STATUS_CODES:
            refreshed_thumbnail_url = self._fetch_fresh_thumbnail_url(video_id, site_name, source_url, thumbnail_url)
            if refreshed_thumbnail_url and refreshed_thumbnail_url != thumbnail_url:
                logger.info(
                    'Retrying thumbnail download with refreshed source URL: video_id=%s, status=%s, site=%s',
                    video_id,
                    response.status_code,
                    site_name or 'unknown',
                )
                thumbnail_url = refreshed_thumbnail_url
                batch_dir, batch_name, file_path = self._storage.target_file_path(video_id, thumbnail_url)
                if os.path.exists(file_path):
                    logger.debug('Thumbnail already exists: %s', file_path)
                    self._local_index.upsert(video_id, batch_name, os.path.basename(file_path), exists=True)
                    return file_path
                response = self._request_thumbnail(video_id, thumbnail_url, site_name, source_url)
                if response is None:
                    return None

        if response.status_code != 200:
            logger.warning(
                'Failed to download thumbnail: video_id=%s, status=%s, url=%s',
                video_id,
                response.status_code,
                thumbnail_url[:80],
            )
            return None

        content_type = response.headers.get('content-type', '')
        if content_type and not content_type.startswith('image/'):
            logger.warning(
                'Invalid content type for thumbnail: video_id=%s, content_type=%s',
                video_id,
                content_type,
            )
            return None

        with open(file_path, 'wb') as f:
            f.write(response.content)

        filename = os.path.basename(file_path)
        self._storage.upsert_batch_index_entry(batch_dir, video_id, filename)
        self._local_index.upsert(video_id, batch_name, filename, exists=True)
        logger.info('Thumbnail downloaded: video_id=%s, path=%s', video_id, file_path)
        return file_path

    def enqueue_download(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str,
        source_url: str | None = None,
    ) -> str | None:
        """Download thumbnail synchronously."""
        return self.download_thumbnail(video_id, thumbnail_url, site_name, source_url=source_url)

    def thumbnail_exists(self, video_id: int) -> bool:
        return self._storage.thumbnail_exists(video_id)

    def existing_thumbnail_ids(self, video_ids: list[int]) -> set[int]:
        return self._storage.existing_thumbnail_ids(video_ids)

    def fetch_thumbnail_url_from_page(self, video_id: int, source_url: str, site_name: str) -> str | None:
        headers = self.build_request_headers(site_name, source_url=source_url, target_url=source_url)
        return self._http_client.fetch_thumbnail_url_from_page(site_name, video_id, source_url, headers)

    def get_thumbnail_url_map(
        self,
        items: list[tuple[int, str | None, str | None]],
    ) -> dict[int, str | None]:
        results: dict[int, str | None] = {}
        offline_enabled_cache: dict[str, bool] = {}
        offline_items: list[tuple[int, str | None, str | None]] = []

        for video_id, remote_url, video_url in items:
            if not remote_url:
                results[video_id] = None
                continue

            site_name = get_site_from_url(video_url) if video_url else None
            if not site_name:
                results[video_id] = remote_url
                continue

            use_offline = offline_enabled_cache.get(site_name)
            if use_offline is None:
                use_offline = self._site_config.should_use_offline(site_name)
                offline_enabled_cache[site_name] = use_offline

            if not use_offline:
                results[video_id] = remote_url
                continue

            offline_items.append((video_id, remote_url, video_url))

        indexed_paths = self._local_index.get_local_thumbnail_path_map(offline_items)

        for video_id, remote_url, _video_url in offline_items:
            indexed_path = indexed_paths.get(video_id)
            if indexed_path:
                results[video_id] = indexed_path
                continue

            local_path = self._storage.get_local_thumbnail_path(video_id, remote_url=remote_url)
            results[video_id] = local_path or remote_url

        return results

    def get_thumbnail_url(self, video_id: int, remote_url: str | None, video_url: str | None = None) -> str | None:
        """Get local static thumbnail URL when available, otherwise the remote URL."""
        return self.get_thumbnail_url_map([
            (video_id, remote_url, video_url),
        ]).get(video_id)

    def _request_thumbnail(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str | None,
        source_url: str | None,
    ):
        headers = self.build_request_headers(site_name, source_url=source_url, target_url=thumbnail_url)
        return self._http_client.request_thumbnail(thumbnail_url, headers, video_id)

    def _fetch_fresh_thumbnail_url(
        self,
        video_id: int,
        site_name: str | None,
        source_url: str | None,
        current_thumbnail_url: str | None,
    ) -> str | None:
        if not site_name or not source_url:
            return None
        if not looks_like_expiring_preview_thumbnail(current_thumbnail_url):
            return None
        return self.fetch_thumbnail_url_from_page(video_id, source_url, site_name)


thumbnail_downloader_service = ThumbnailDownloaderService()
