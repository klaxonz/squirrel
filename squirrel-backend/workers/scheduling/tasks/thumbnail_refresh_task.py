import html as html_lib
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import suppress

import httpx
from sqlalchemy import func, select

from domains.video.application.services.extraction.thumbnail_downloader import thumbnail_downloader_service
from domains.video.domain.models.video import Video
from infrastructure.database.session import get_session
from infrastructure.runtime.site_config_manager import get_effective_site_catalog
from infrastructure.scheduling.base import BaseTask, TaskRegistry

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}

_LDJSON_THUMBNAIL_RE = re.compile(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', re.IGNORECASE | re.DOTALL)
_META_THUMBNAIL_PATTERNS = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.IGNORECASE),
)

_SUPPORTED_SITE_PATTERNS = {
    "pornhub": "%pornhub.com%",
    "youporn": "%youporn.com%",
}
_PAGE_FETCH_MAX_ATTEMPTS = 3
_PAGE_FETCH_RETRYABLE_STATUS_CODES = {403, 408, 425, 429, 500, 502, 503, 504}

# Global HTTP client, reuse connections
_shared_http_client: httpx.Client | None = None
_client_lock_time = 0.0
_CLIENT_TTL = 300.0  # 5 minutes
_http_client_lock = threading.Lock()

def _get_shared_http_client() -> httpx.Client:
    """Get the shared HTTP client"""
    global _shared_http_client, _client_lock_time

    with _http_client_lock:
        now = time.time()
        if _shared_http_client is None or now - _client_lock_time > _CLIENT_TTL:
            if _shared_http_client:
                with suppress(Exception):
                    _shared_http_client.close()

            _shared_http_client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers=_HEADERS,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
            _client_lock_time = now

        return _shared_http_client


@TaskRegistry.register(interval=60 * 24, unit="minutes", start_immediately=True)
class ThumbnailRefreshTask(BaseTask):
    """Periodically backfill thumbnail cache for sites supporting offline thumbnails."""

    @classmethod
    def _batch_check_thumbnails(cls, video_ids: list[int]) -> set[int]:
        """Batch check whether thumbnails exist for multiple videos
        Returns the set of video_ids that already have thumbnails
        """
        from domains.video.application.services.extraction.thumbnail_downloader import thumbnail_downloader_service

        existing_ids = set()

        # Group by batch to avoid re-scanning the same directory
        batch_groups: dict[str, list[int]] = {}
        for video_id in video_ids:
            batch_dir = thumbnail_downloader_service._get_batch_dir(video_id)
            if batch_dir not in batch_groups:
                batch_groups[batch_dir] = []
            batch_groups[batch_dir].append(video_id)

        # Fetch index once per batch, then check all video_ids
        for batch_dir, ids_in_batch in batch_groups.items():
            batch_index = thumbnail_downloader_service._get_batch_index(batch_dir)
            for video_id in ids_in_batch:
                if video_id in batch_index:
                    existing_ids.add(video_id)

        return existing_ids

    @classmethod
    def _extract_thumbnail_url(cls, html: str) -> str | None:
        """Extract a thumbnail URL from JSON-LD or social preview metadata."""
        for match in _LDJSON_THUMBNAIL_RE.finditer(html):
            try:
                data = json.loads(match.group(1).strip())
            except (json.JSONDecodeError, TypeError):
                continue

            candidates = data if isinstance(data, list) else [data]
            for item in candidates:
                if not isinstance(item, dict):
                    continue
                thumbnail_url = item.get("thumbnailUrl")
                if thumbnail_url:
                    return str(thumbnail_url).strip()

        for pattern in _META_THUMBNAIL_PATTERNS:
            match = pattern.search(html)
            if not match:
                continue
            thumbnail_url = html_lib.unescape(match.group(1).strip())
            if thumbnail_url:
                return thumbnail_url

        return None

    @classmethod
    def _get_refresh_targets(cls) -> list[tuple[str, str]]:
        catalog = get_effective_site_catalog()
        targets: list[tuple[str, str]] = []

        for site_name, url_pattern in _SUPPORTED_SITE_PATTERNS.items():
            site_info = catalog.get(site_name, {})
            metadata = site_info.get("metadata") or {}
            if not site_info.get("enabled", True):
                continue
            if not metadata.get("offline_thumbnails_download", False):
                continue
            targets.append((site_name, url_pattern))

        return targets

    @staticmethod
    def _build_page_fetch_retry_delay(attempt: int) -> float:
        return min(5.0, 0.8 * attempt)

    @staticmethod
    def _get_site_max_workers(site_name: str) -> int:
        if str(site_name).lower() == "pornhub":
            return 4
        return 8

    @classmethod
    def _get_stored_thumbnail_url(cls, video: Video) -> str | None:
        stored_thumbnail = str(video.thumbnail or "").strip()
        return stored_thumbnail or None

    @classmethod
    def _fetch_thumbnail_url_from_page(cls, video: Video, site_name: str) -> str | None:
        client = _get_shared_http_client()
        headers = thumbnail_downloader_service.build_request_headers(
            site_name,
            source_url=video.url,
            target_url=video.url,
        )
        response: httpx.Response | None = None

        for attempt in range(1, _PAGE_FETCH_MAX_ATTEMPTS + 1):
            response = client.get(video.url, headers=headers)
            if response.status_code == 200:
                return cls._extract_thumbnail_url(response.text)

            if (
                response.status_code in _PAGE_FETCH_RETRYABLE_STATUS_CODES
                and attempt < _PAGE_FETCH_MAX_ATTEMPTS
            ):
                logger.info(
                    "[ThumbnailRefreshTask] Retrying page thumbnail fetch: site=%s video id=%s status=%s attempt=%s/%s",
                    site_name,
                    video.id,
                    response.status_code,
                    attempt,
                    _PAGE_FETCH_MAX_ATTEMPTS,
                )
                time.sleep(cls._build_page_fetch_retry_delay(attempt))
                continue

            logger.warning(
                "[ThumbnailRefreshTask] Failed to fetch page: site=%s video id=%s status=%s",
                site_name,
                video.id,
                response.status_code,
            )
            return None

        return None

    @classmethod
    def _resolve_thumbnail_url(cls, video: Video, site_name: str) -> str | None:
        return cls._get_stored_thumbnail_url(video) or cls._fetch_thumbnail_url_from_page(video, site_name)

    @classmethod
    def run(cls):
        logger.info("[ThumbnailRefreshTask] Start refreshing video thumbnails")

        batch_size = 100
        processed_count = 0
        total_checked = 0
        refresh_targets = cls._get_refresh_targets()

        if not refresh_targets:
            logger.info("[ThumbnailRefreshTask] No enabled sites require thumbnail refresh")
            return

        for site_name, url_pattern in refresh_targets:
            max_workers = cls._get_site_max_workers(site_name)
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                last_id: int | None = None
                site_checked = 0

                with get_session() as session:
                    total_site_videos = session.scalar(
                        select(func.count(Video.id)).where(Video.url.like(url_pattern)),
                    )

                logger.info(
                    "[ThumbnailRefreshTask] Total %s videos to check: %d",
                    site_name,
                    total_site_videos,
                )

                while True:
                    with get_session() as session:
                        query = select(Video).where(Video.url.like(url_pattern)).order_by(Video.id.desc())
                        if last_id is not None:
                            query = query.where(Video.id < last_id)
                        rows: list[Video] = session.scalars(query.limit(batch_size)).all()

                    if not rows:
                        break

                    video_ids = [video.id for video in rows]
                    existing_thumbnails = cls._batch_check_thumbnails(video_ids)

                    videos_to_process = []
                    for video in rows:
                        total_checked += 1
                        site_checked += 1
                        if video.id not in existing_thumbnails:
                            videos_to_process.append(video)

                    if videos_to_process:
                        futures = [
                            executor.submit(cls._process_single_video, video, site_name)
                            for video in videos_to_process
                        ]

                        for future in as_completed(futures):
                            try:
                                future.result()
                                processed_count += 1
                            except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
                                logger.exception(
                                    "[ThumbnailRefreshTask] error processing video: %s", e,
                                )

                    if total_site_videos > 0:
                        progress_pct = (site_checked / total_site_videos * 100)
                        logger.info(
                            "[ThumbnailRefreshTask] Site %s batch checked %d/%d videos (%.1f%%), processed %d thumbnails",
                            site_name,
                            min(total_site_videos, site_checked),
                            total_site_videos,
                            progress_pct,
                            processed_count,
                        )

                    last_id = rows[-1].id

        logger.info(
            "[ThumbnailRefreshTask] Finished: checked %d videos, processed %d thumbnails",
            total_checked,
            processed_count,
        )

    @classmethod
    def _process_single_video(cls, video: Video, site_name: str) -> None:
        try:
            stored_thumbnail_url = cls._get_stored_thumbnail_url(video)
            thumbnail_url = stored_thumbnail_url or cls._fetch_thumbnail_url_from_page(video, site_name)
            if not thumbnail_url:
                logger.warning(
                    "[ThumbnailRefreshTask] No thumbnail found for site=%s video id=%s",
                    site_name,
                    video.id,
                )
                return

            downloaded_path = thumbnail_downloader_service.download_thumbnail(
                video.id,
                thumbnail_url,
                site_name,
                source_url=video.url,
            )
            if downloaded_path:
                logger.info(
                    "[ThumbnailRefreshTask] Downloaded thumbnail for site=%s video id=%s",
                    site_name,
                    video.id,
                )
                return

            if stored_thumbnail_url:
                page_thumbnail_url = cls._fetch_thumbnail_url_from_page(video, site_name)
                if page_thumbnail_url and page_thumbnail_url != stored_thumbnail_url:
                    downloaded_path = thumbnail_downloader_service.download_thumbnail(
                        video.id,
                        page_thumbnail_url,
                        site_name,
                        source_url=video.url,
                    )
                    if downloaded_path:
                        logger.info(
                            "[ThumbnailRefreshTask] Downloaded thumbnail from page fallback for site=%s video id=%s",
                            site_name,
                            video.id,
                        )
                        return

            logger.warning(
                "[ThumbnailRefreshTask] Failed to cache thumbnail for site=%s video id=%s",
                site_name,
                video.id,
            )

        except Exception as e:  # task boundary -- prevent single failure from crashing scheduler
            logger.warning(
                "[ThumbnailRefreshTask] Failed to process site=%s video id=%s url=%s: %s",
                site_name,
                video.id,
                video.url,
                e,
            )
