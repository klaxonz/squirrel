"""Thumbnail download service - handles downloading thumbnails to local storage
"""
import html as html_lib
import json
import logging
import os
import re
import time
from collections import OrderedDict
from datetime import datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import select

from common.site_constants import SITE_META_OFFLINE_THUMBNAILS_DISPLAY, SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD
from core.config import settings
from core.database import get_session
from core.site_config_manager import get_effective_site_catalog
from models.video_thumbnail_local_index import VideoThumbnailLocalIndex
from utils.cookie import filter_cookies_to_query_string
from utils.url_helper import get_site_from_url

logger = logging.getLogger(__name__)

BATCH_SIZE = 1000
SUPPORTED_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".avif")
_EFFECTIVE_CATALOG_CACHE_TTL = 10.0
_BATCH_INDEX_CACHE_TTL = 300.0
_BATCH_INDEX_CACHE_MAX_BATCHES = 64
_THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS = 3
_THUMBNAIL_DOWNLOAD_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
_EXPIRING_PREVIEW_REFRESH_STATUS_CODES = {403, 404, 410, 472}
_LDJSON_THUMBNAIL_RE = re.compile(r'<script\s+type=["\']application/ld\+json["\']>(.*?)</script>', re.IGNORECASE | re.DOTALL)
_META_THUMBNAIL_PATTERNS = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.IGNORECASE),
)

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

_SITE_COOKIE_DEFAULTS: dict[str, dict[str, str]] = {
    "pornhub": {
        "age_verified": "1",
        "accessAgeDisclaimerPH": "1",
        "accessAgeDisclaimerUK": "1",
        "accessPH": "1",
    },
}


class ThumbnailDownloaderService:
    """Thumbnail download service

    Responsibilities:
    - Check site configuration
    - Download thumbnails to local storage
    - Manage thumbnail storage directories
    """

    def __init__(self):
        self._http_client: httpx.Client | None = None
        self._effective_catalog: dict | None = None
        self._effective_catalog_cached_at = 0.0
        self._batch_index_cache: OrderedDict[str, tuple[dict[int, str], float]] = OrderedDict()

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers=_DEFAULT_HEADERS,
            )
        return self._http_client

    def close(self) -> None:
        if self._http_client is None:
            return
        try:
            self._http_client.close()
        except (OSError, ValueError, TypeError):
            pass
        self._http_client = None

    def _reset_http_client(self) -> None:
        self.close()

    def _request_thumbnail(
        self,
        target_url: str,
        site_name: str | None,
        source_url: str | None,
        video_id: int,
    ) -> httpx.Response | None:
        headers = self.build_request_headers(
            site_name,
            source_url=source_url,
            target_url=target_url,
        )
        resp: httpx.Response | None = None

        for attempt in range(1, _THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS + 1):
            try:
                client = self._get_http_client()
                resp = client.get(target_url, headers=headers)
            except httpx.TransportError as exc:
                if attempt >= _THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS:
                    raise

                logger.info(
                    "Retrying thumbnail download after transport error: "
                    "video_id=%s, attempt=%s/%s, url=%s, error=%s",
                    video_id,
                    attempt,
                    _THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS,
                    target_url[:80],
                    exc,
                )
                self._reset_http_client()
                time.sleep(self._build_retry_delay(attempt))
                continue

            if resp.status_code == 200:
                return resp

            if (
                self._should_retry_download_status(resp.status_code)
                and attempt < _THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS
            ):
                logger.info(
                    "Retrying thumbnail download after HTTP %s: "
                    "video_id=%s, attempt=%s/%s, url=%s",
                    resp.status_code,
                    video_id,
                    attempt,
                    _THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS,
                    target_url[:80],
                )
                time.sleep(self._build_retry_delay(attempt))
                continue

            return resp

        return resp

    @staticmethod
    def _parse_cookie_header(cookie_header: str | None) -> dict[str, str]:
        cookies: dict[str, str] = {}
        for segment in str(cookie_header or "").split(";"):
            item = segment.strip()
            if not item or "=" not in item:
                continue
            name, value = item.split("=", 1)
            clean_name = name.strip()
            if not clean_name:
                continue
            cookies[clean_name] = value.strip()
        return cookies

    def _site_info(self, site_name: str | None) -> dict:
        if not site_name:
            return {}
        return self._get_effective_catalog().get(site_name.lower(), {})

    def _site_requires_cookies(self, site_name: str | None) -> bool:
        metadata = (self._site_info(site_name).get("metadata") or {})
        return bool(metadata.get("requires_cookies"))

    def build_request_headers(
        self,
        site_name: str | None,
        *,
        source_url: str | None = None,
        target_url: str | None = None,
    ) -> dict[str, str]:
        headers = dict(_DEFAULT_HEADERS)
        if not site_name:
            return headers

        site_info = self._site_info(site_name)
        http_headers = (site_info.get("http") or {}).get("headers") or {}
        for key, value in http_headers.items():
            if value is not None:
                headers[str(key)] = str(value)

        effective_referer = str(source_url or headers.get("Referer") or "").strip()
        if effective_referer:
            headers["Referer"] = effective_referer

        referer = headers.get("Referer")
        if referer and "Origin" not in headers:
            try:
                parsed = urlparse(referer)
                if parsed.scheme and parsed.netloc:
                    headers["Origin"] = f"{parsed.scheme}://{parsed.netloc}"
            except (ValueError, TypeError):
                pass

        if self._site_requires_cookies(site_name):
            cookies = self._parse_cookie_header(headers.get("Cookie"))
            cookie_lookup_url = source_url or target_url
            if cookie_lookup_url:
                cookies.update(self._parse_cookie_header(filter_cookies_to_query_string(cookie_lookup_url)))

            for name, value in _SITE_COOKIE_DEFAULTS.get(str(site_name).lower(), {}).items():
                cookies.setdefault(name, value)

            if cookies:
                headers["Cookie"] = "; ".join(f"{name}={value}" for name, value in cookies.items())

        return headers

    def _get_effective_catalog(self) -> dict:
        now = time.time()
        if (
            self._effective_catalog is None
            or now - self._effective_catalog_cached_at > _EFFECTIVE_CATALOG_CACHE_TTL
        ):
            self._effective_catalog = get_effective_site_catalog()
            self._effective_catalog_cached_at = now
        return self._effective_catalog

    def _evict_batch_index_cache(self) -> None:
        while len(self._batch_index_cache) > _BATCH_INDEX_CACHE_MAX_BATCHES:
            self._batch_index_cache.popitem(last=False)

    def _scan_batch_index(self, batch_dir: str) -> dict[int, str]:
        if not os.path.isdir(batch_dir):
            return {}

        index: dict[int, str] = {}
        with os.scandir(batch_dir) as it:
            for entry in it:
                if not entry.is_file():
                    continue
                name = entry.name
                base, ext = os.path.splitext(name)
                ext = ext.lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue
                try:
                    video_id = int(base)
                except ValueError:
                    continue
                index[video_id] = name
        return index

    def _get_batch_index(self, batch_dir: str) -> dict[int, str]:
        now = time.time()
        cached = self._batch_index_cache.get(batch_dir)
        if cached is not None:
            index, cached_at = cached
            if now - cached_at <= _BATCH_INDEX_CACHE_TTL:
                self._batch_index_cache.move_to_end(batch_dir)
                return index

        index = self._scan_batch_index(batch_dir)
        self._batch_index_cache[batch_dir] = (index, now)
        self._batch_index_cache.move_to_end(batch_dir)
        self._evict_batch_index_cache()
        return index

    def _upsert_batch_index_entry(self, batch_dir: str, video_id: int, filename: str) -> None:
        cached = self._batch_index_cache.get(batch_dir)
        if cached is None:
            return
        index, _ = cached
        index[video_id] = filename
        self._batch_index_cache[batch_dir] = (index, time.time())
        self._batch_index_cache.move_to_end(batch_dir)

    def _build_static_thumbnail_url(self, batch_name: str, filename: str) -> str:
        return f"/static/thumbnails/{batch_name}/{filename}"

    @staticmethod
    def _should_retry_download_status(status_code: int) -> bool:
        return status_code in _THUMBNAIL_DOWNLOAD_RETRYABLE_STATUS_CODES

    @staticmethod
    def _build_retry_delay(attempt: int) -> float:
        return min(2.0, 0.5 * attempt)

    @staticmethod
    def _looks_like_expiring_preview_thumbnail(url: str | None) -> bool:
        normalized = str(url or "").strip().lower()
        if not normalized:
            return False
        if "phncdn.com/videos/" in normalized:
            return True
        return "/plain/" in normalized and (
            "validto=" in normalized or "hdnea=" in normalized
        )

    @staticmethod
    def _thumbnail_expiry_score(url: str) -> float:
        normalized = str(url or "").strip().lower()
        if not normalized:
            return -1
        if not any(token in normalized for token in ("validto=", "hdnea=", "hmac=", "hash=")):
            return float("inf")

        validto_match = re.search(r"[?&]validto=(\d+)", normalized)
        if validto_match:
            return float(validto_match.group(1))

        hdnea_exp_match = re.search(r"(?:^|[~&])exp=(\d+)", normalized)
        if hdnea_exp_match:
            return float(hdnea_exp_match.group(1))

        return 0

    def _pick_best_thumbnail_url(self, thumbnail_urls: list[str]) -> str | None:
        unique_urls = []
        for thumbnail_url in thumbnail_urls:
            normalized = html_lib.unescape(str(thumbnail_url or "").strip())
            if normalized and normalized not in unique_urls:
                unique_urls.append(normalized)

        if not unique_urls:
            return None

        return max(unique_urls, key=self._thumbnail_expiry_score)

    def _extract_thumbnail_url_from_html(self, html_text: str) -> str | None:
        thumbnail_urls: list[str] = []
        for match in _LDJSON_THUMBNAIL_RE.finditer(str(html_text or "")):
            try:
                payload = json.loads(match.group(1).strip())
            except (json.JSONDecodeError, TypeError):
                continue

            pending = payload if isinstance(payload, list) else [payload]
            while pending:
                item = pending.pop(0)
                if isinstance(item, list):
                    pending.extend(item)
                    continue
                if not isinstance(item, dict):
                    continue

                graph = item.get("@graph")
                if isinstance(graph, list):
                    pending.extend(graph)
                elif isinstance(graph, dict):
                    pending.append(graph)

                for key in ("thumbnailUrl", "thumbnail", "contentUrl"):
                    value = item.get(key)
                    if isinstance(value, str) and value.strip():
                        thumbnail_urls.append(value.strip())
                    if isinstance(value, list):
                        for candidate in value:
                            if isinstance(candidate, str) and candidate.strip():
                                thumbnail_urls.append(candidate.strip())

        for pattern in _META_THUMBNAIL_PATTERNS:
            for match in pattern.finditer(str(html_text or "")):
                thumbnail_url = html_lib.unescape(match.group(1).strip())
                if thumbnail_url:
                    thumbnail_urls.append(thumbnail_url)

        return self._pick_best_thumbnail_url(thumbnail_urls)

    def _fetch_fresh_thumbnail_url(
        self,
        site_name: str | None,
        source_url: str | None,
        current_thumbnail_url: str | None,
    ) -> str | None:
        if not site_name or not source_url:
            return None
        if not self._looks_like_expiring_preview_thumbnail(current_thumbnail_url):
            return None

        headers = self.build_request_headers(
            site_name,
            source_url=source_url,
            target_url=source_url,
        )

        try:
            response = self._get_http_client().get(source_url, headers=headers)
        except httpx.TransportError as exc:
            logger.info(
                "Failed to refresh expiring thumbnail from source page: site=%s, url=%s, error=%s",
                site_name,
                source_url[:120],
                exc,
            )
            self._reset_http_client()
            return None

        if response.status_code != 200:
            logger.info(
                "Failed to refresh expiring thumbnail from source page: site=%s, "
                "url=%s, status=%s",
                site_name,
                source_url[:120],
                response.status_code,
            )
            return None

        refreshed_thumbnail_url = self._extract_thumbnail_url_from_html(response.text)
        if not refreshed_thumbnail_url or refreshed_thumbnail_url == current_thumbnail_url:
            return None
        return refreshed_thumbnail_url

    def _upsert_local_thumbnail_index(
        self,
        video_id: int,
        batch_name: str,
        filename: str,
        exists: bool = True,
    ) -> None:
        now = datetime.now()
        try:
            with get_session() as session:
                record = session.scalars(
                    select(VideoThumbnailLocalIndex)
                    .where(VideoThumbnailLocalIndex.video_id == video_id),
                ).first()
                if record is None:
                    session.add(VideoThumbnailLocalIndex(
                        video_id=video_id,
                        batch_name=batch_name,
                        filename=filename,
                        exists=exists,
                        indexed_at=now,
                        created_at=now,
                        updated_at=now,
                    ))
                    return

                record.batch_name = batch_name
                record.filename = filename
                record.exists = exists
                record.indexed_at = now
                record.updated_at = now
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.warning("Failed to update thumbnail local index: video_id=%s, error=%s", video_id, e)

    def _get_local_thumbnail_path_map(
        self,
        indexed_items: list[tuple[int, str | None, str | None]],
    ) -> dict[int, str]:
        video_ids = [video_id for video_id, _remote_url, _video_url in indexed_items]
        if not video_ids:
            return {}

        try:
            with get_session() as session:
                rows = session.execute(
                    select(
                        VideoThumbnailLocalIndex.video_id,
                        VideoThumbnailLocalIndex.batch_name,
                        VideoThumbnailLocalIndex.filename,
                    )
                    .where(
                        VideoThumbnailLocalIndex.video_id.in_(video_ids),
                        VideoThumbnailLocalIndex.exists.is_(True),
                    ),
                ).all()
        except (ConnectionError, OSError, ValueError, TypeError) as e:
            logger.warning("Failed to read thumbnail local index: error=%s", e)
            return {}

        results: dict[int, str] = {}

        for row in rows:
            file_path = os.path.join(str(settings.thumbnails_dir), row.batch_name, row.filename)
            if os.path.exists(file_path):
                results[row.video_id] = self._build_static_thumbnail_url(row.batch_name, row.filename)
                continue

            self._upsert_local_thumbnail_index(
                row.video_id,
                row.batch_name,
                row.filename,
                exists=False,
            )

        return results

    def download_thumbnail(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str | None = None,
        source_url: str | None = None,
    ) -> str | None:
        """Download thumbnail to local storage

        Args:
            video_id: Video ID
            thumbnail_url: Thumbnail URL
            site_name: Site name (optional, for configuration check)
            source_url: Source page URL used to derive referer and cookies

        Returns:
            Local file path, or None on failure

        """
        if not thumbnail_url:
            return None

        if site_name and not self._should_download(site_name):
            logger.debug("Thumbnail download disabled for site: %s", site_name)
            return None

        try:
            batch_dir = self._get_batch_dir(video_id)
            os.makedirs(batch_dir, exist_ok=True)

            ext = self._get_extension(thumbnail_url)
            file_path = os.path.join(batch_dir, f"{video_id}{ext}")
            batch_name = os.path.basename(batch_dir)

            if os.path.exists(file_path):
                logger.debug("Thumbnail already exists: %s", file_path)
                self._upsert_local_thumbnail_index(video_id, batch_name, os.path.basename(file_path), exists=True)
                return file_path

            resp = self._request_thumbnail(thumbnail_url, site_name, source_url, video_id)
            if resp is None:
                return None

            if resp.status_code != 200 and resp.status_code in _EXPIRING_PREVIEW_REFRESH_STATUS_CODES:
                refreshed_thumbnail_url = self._fetch_fresh_thumbnail_url(
                    site_name,
                    source_url,
                    thumbnail_url,
                )
                if refreshed_thumbnail_url and refreshed_thumbnail_url != thumbnail_url:
                    logger.info(
                        "Retrying thumbnail download with refreshed source URL: "
                        "video_id=%s, status=%s, site=%s",
                        video_id,
                        resp.status_code,
                        site_name or "unknown",
                    )
                    thumbnail_url = refreshed_thumbnail_url
                    ext = self._get_extension(thumbnail_url)
                    file_path = os.path.join(batch_dir, f"{video_id}{ext}")

                    if os.path.exists(file_path):
                        logger.debug("Thumbnail already exists: %s", file_path)
                        self._upsert_local_thumbnail_index(video_id, batch_name, os.path.basename(file_path), exists=True)
                        return file_path

                    resp = self._request_thumbnail(thumbnail_url, site_name, source_url, video_id)
                    if resp is None:
                        return None

            if resp.status_code != 200:
                logger.warning("Failed to download thumbnail: video_id=%s, status=%s, url=%s", video_id, resp.status_code, thumbnail_url[:80])
                return None

            content_type = resp.headers.get("content-type", "")
            if content_type and not content_type.startswith("image/"):
                logger.warning("Invalid content type for thumbnail: video_id=%s, content_type=%s", video_id, content_type)
                return None

            with open(file_path, "wb") as f:
                f.write(resp.content)

            self._upsert_batch_index_entry(batch_dir, video_id, os.path.basename(file_path))
            self._upsert_local_thumbnail_index(video_id, batch_name, os.path.basename(file_path), exists=True)
            logger.info("Thumbnail downloaded: video_id=%s, path=%s", video_id, file_path)
            return file_path

        except (OSError, ValueError, TypeError) as e:
            logger.warning("Failed to download thumbnail: video_id=%s, url=%s, error=%s", video_id, thumbnail_url[:80], e)
            return None

    def enqueue_download(
        self,
        video_id: int,
        thumbnail_url: str,
        site_name: str,
        source_url: str | None = None,
    ) -> str | None:
        """Download thumbnail (synchronous execution)

        Args:
            video_id: Video ID
            thumbnail_url: Thumbnail URL
            site_name: Site name
            source_url: Source page URL used to derive referer and cookies

        Returns:
            Local file path, or None on failure

        """
        return self.download_thumbnail(video_id, thumbnail_url, site_name, source_url=source_url)

    def _should_download(self, site_name: str) -> bool:
        """Check whether thumbnails should be downloaded for this site"""
        try:
            catalog = self._get_effective_catalog()
            site_info = catalog.get(site_name.lower(), {})
            metadata = site_info.get("metadata", {})
            return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DOWNLOAD, False)
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.warning("Failed to check thumbnail config: %s", e)
            return False

    def _get_batch_dir(self, video_id: int) -> str:
        """Get the batch directory for a video id"""
        batch_num = (video_id - 1) // BATCH_SIZE + 1
        batch_name = f"batch_{batch_num:03d}"
        return os.path.join(str(settings.thumbnails_dir), batch_name)

    def _get_extension(self, url: str) -> str:
        """Extract file extension from URL"""
        try:
            parsed = urlparse(url)
            path = parsed.path
            _, ext = os.path.splitext(path)
            if ext and ext.lower() in SUPPORTED_EXTENSIONS:
                return ext.lower()
        except (ValueError, TypeError):
            pass
        return ".jpg"

    def thumbnail_exists(self, video_id: int) -> bool:
        """Check whether thumbnail already exists"""
        batch_dir = self._get_batch_dir(video_id)
        return video_id in self._get_batch_index(batch_dir)

    def _get_local_thumbnail_path(self, video_id: int, remote_url: str | None = None) -> str | None:
        """Get local thumbnail static URL path"""
        batch_dir = self._get_batch_dir(video_id)
        batch_name = os.path.basename(batch_dir)

        if remote_url:
            filename = f"{video_id}{self._get_extension(remote_url)}"
            file_path = os.path.join(batch_dir, filename)
            if os.path.exists(file_path):
                return self._build_static_thumbnail_url(batch_name, filename)
            return None

        batch_index = self._get_batch_index(batch_dir)
        filename = batch_index.get(video_id)
        if filename is None:
            return None
        return self._build_static_thumbnail_url(batch_name, filename)

    def _should_use_offline(self, site_name: str) -> bool:
        """Check whether to use offline thumbnails for this site"""
        try:
            catalog = self._get_effective_catalog()
            site_info = catalog.get(site_name.lower(), {})
            metadata = site_info.get("metadata", {})
            return metadata.get(SITE_META_OFFLINE_THUMBNAILS_DISPLAY, False)
        except (ValueError, TypeError, AttributeError, KeyError) as e:
            logger.warning("Failed to check thumbnail display config: %s", e)
            return False

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
                use_offline = self._should_use_offline(site_name)
                offline_enabled_cache[site_name] = use_offline

            if not use_offline:
                results[video_id] = remote_url
                continue

            offline_items.append((video_id, remote_url, video_url))

        indexed_paths = self._get_local_thumbnail_path_map(offline_items)

        for video_id, remote_url, _video_url in offline_items:
            indexed_path = indexed_paths.get(video_id)
            if indexed_path:
                results[video_id] = indexed_path
                continue

            local_path = self._get_local_thumbnail_path(video_id, remote_url=remote_url)
            results[video_id] = local_path or remote_url

        return results

    def get_thumbnail_url(self, video_id: int, remote_url: str | None, video_url: str | None = None) -> str | None:
        """Get the full thumbnail URL

        Args:
            video_id: Video ID
            remote_url: Remote thumbnail URL
            video_url: Video URL (used to derive site name)

        Returns:
            Local static path or remote URL

        """
        return self.get_thumbnail_url_map([
            (video_id, remote_url, video_url),
        ]).get(video_id)


thumbnail_downloader_service = ThumbnailDownloaderService()
