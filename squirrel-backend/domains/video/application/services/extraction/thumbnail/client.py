import logging
import time

import httpx

from domains.video.application.services.extraction.thumbnail.headers import DEFAULT_HEADERS
from domains.video.application.services.extraction.thumbnail.html import extract_thumbnail_url_from_html

logger = logging.getLogger(__name__)

THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS = 3
THUMBNAIL_DOWNLOAD_RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504}
PAGE_FETCH_MAX_ATTEMPTS = 3
PAGE_FETCH_RETRYABLE_STATUS_CODES = {403, 408, 425, 429, 500, 502, 503, 504}


class ThumbnailHttpClient:
    """HTTP client and retry policy for thumbnail-related requests."""

    def __init__(self) -> None:
        self._http_client: httpx.Client | None = None

    def close(self) -> None:
        if self._http_client is None:
            return
        self._http_client.close()
        self._http_client = None

    def request_thumbnail(
        self,
        target_url: str,
        headers: dict[str, str],
        video_id: int,
    ) -> httpx.Response | None:
        response: httpx.Response | None = None
        for attempt in range(1, THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS + 1):
            try:
                response = self._get_http_client().get(target_url, headers=headers)
            except httpx.TransportError as exc:
                if attempt >= THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS:
                    raise

                logger.info(
                    'Retrying thumbnail download after transport error: video_id=%s, attempt=%s/%s, url=%s, error=%s',
                    video_id,
                    attempt,
                    THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS,
                    target_url[:80],
                    exc,
                )
                self.close()
                time.sleep(self._download_retry_delay(attempt))
                continue

            if response.status_code == 200:
                return response

            if (
                response.status_code in THUMBNAIL_DOWNLOAD_RETRYABLE_STATUS_CODES
                and attempt < THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS
            ):
                logger.info(
                    'Retrying thumbnail download after HTTP %s: video_id=%s, attempt=%s/%s, url=%s',
                    response.status_code,
                    video_id,
                    attempt,
                    THUMBNAIL_DOWNLOAD_MAX_ATTEMPTS,
                    target_url[:80],
                )
                time.sleep(self._download_retry_delay(attempt))
                continue

            return response

        return response

    def fetch_thumbnail_url_from_page(
        self,
        site_name: str,
        video_id: int,
        source_url: str,
        headers: dict[str, str],
    ) -> str | None:
        for attempt in range(1, PAGE_FETCH_MAX_ATTEMPTS + 1):
            response = self._get_http_client().get(source_url, headers=headers)
            if response.status_code == 200:
                return extract_thumbnail_url_from_html(response.text)

            if response.status_code in PAGE_FETCH_RETRYABLE_STATUS_CODES and attempt < PAGE_FETCH_MAX_ATTEMPTS:
                logger.info(
                    'Retrying page thumbnail fetch: site=%s video_id=%s status=%s attempt=%s/%s',
                    site_name,
                    video_id,
                    response.status_code,
                    attempt,
                    PAGE_FETCH_MAX_ATTEMPTS,
                )
                time.sleep(self._page_retry_delay(attempt))
                continue

            logger.warning(
                'Failed to fetch page thumbnail: site=%s video_id=%s status=%s',
                site_name,
                video_id,
                response.status_code,
            )
            return None

        return None

    def _get_http_client(self) -> httpx.Client:
        if self._http_client is None:
            self._http_client = httpx.Client(
                timeout=30.0,
                follow_redirects=True,
                headers=DEFAULT_HEADERS,
                limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
            )
        return self._http_client

    @staticmethod
    def _download_retry_delay(attempt: int) -> float:
        return min(2.0, 0.5 * attempt)

    @staticmethod
    def _page_retry_delay(attempt: int) -> float:
        return min(5.0, 0.8 * attempt)
