from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
    build_cookie_header,
    fetch_page_thumbnail_url,
    get_http_headers,
    normalize_thumbnail,
    resolve_cookie_file_path,
)

try:
    from yt_dlp import YoutubeDL as _YoutubeDL
except ImportError:
    _YoutubeDL = None


logger = logging.getLogger(__name__)
YoutubeDL = _YoutubeDL

SITE_DOMAIN = 'youporn.com'
SITE_URL = f'https://www.{SITE_DOMAIN}'
DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
)
AGE_GATE_COOKIES = {
    'showAgeDisclaimer': '1',
    'access': '1',
    'accessPH': '1',
}


class YouPornExtractor(YoutubeDLExtractorBase):
    """YouPorn video extractor backed by yt-dlp."""

    site_name = 'youporn'
    supported_domains = ['youporn.com']
    url_patterns = ['youporn.com/watch/']

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        if YoutubeDL is None:
            raise ParseError('yt-dlp is not installed', context={'url': url, 'site_name': self.site_name})

        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                if video_info:
                    self._process_youporn_info(video_info, url)
                return video_info
        except Exception as exc:  # SDK boundary — translate yt-dlp errors to domain types
            error_msg = str(exc).lower()
            context = {'url': url, 'original_error': str(exc)}

            if any(token in error_msg for token in ('login', 'private', 'sign in')):
                raise AuthError(f'Login is required to access: {url}', context=context) from exc
            if any(token in error_msg for token in ('404', 'not found', 'removed', 'deleted', 'unavailable')):
                raise NotFoundError(f'Video does not exist or has been removed: {url}', context=context) from exc
            if any(token in error_msg for token in ('timeout', 'connection', 'network', 'temporarily unavailable')):
                raise NetworkError(f'Network request failed: {url}', context=context) from exc

            logger.error('YouPorn extraction failed: %s', url, exc_info=True)
            raise ParseError(f'Failed to extract YouPorn video info: {exc}', context=context) from exc

    def _build_ytdlp_opts(self, url: str, queue_name: str | None = None) -> dict[str, Any]:
        cookie_file = resolve_cookie_file_path(url)
        headers = self._build_ytdlp_headers(url, cookie_file)
        ydl_opts: dict[str, Any] = {
            'quiet': True,
            'skip_download': True,
            'socket_timeout': 30,
            'retries': 5,
            'extractor_retries': 3,
            'fragment_retries': 5,
            'file_access_retries': 3,
            'ignoreerrors': False,
            'noprogress': True,
            'noplaylist': True,
            'http_headers': headers,
        }
        if cookie_file:
            ydl_opts['cookiefile'] = cookie_file
        return apply_ytdlp_rate_limit(self.site_name, ydl_opts)

    def _process_youporn_info(self, video_info: dict[str, Any], source_url: str | None = None) -> None:
        try:
            timestamp = video_info.get('timestamp')
            if timestamp:
                video_info['publish_date'] = datetime.fromtimestamp(timestamp)
            normalize_thumbnail(video_info, source_url, self._fetch_page_thumbnail_url)
        except (ValueError, TypeError) as exc:
            logger.warning('Failed to process YouPorn video info: %s', exc)

    def _fetch_page_thumbnail_url(self, url: str) -> str | None:
        cookie_file = resolve_cookie_file_path(url)
        return fetch_page_thumbnail_url(url, cookie_file, self._build_ytdlp_headers)

    def _build_ytdlp_headers(self, url: str, cookie_file: str | None) -> dict[str, str]:
        headers = get_http_headers(
            self.site_name,
            {
                'User-Agent': DEFAULT_USER_AGENT,
                'Referer': f'{SITE_URL}/',
                'Accept-Language': 'en-US,en;q=0.9',
                'Origin': SITE_URL,
            },
        )
        headers.setdefault('User-Agent', DEFAULT_USER_AGENT)
        headers.setdefault('Accept-Language', 'en-US,en;q=0.9')
        headers.setdefault('Origin', SITE_URL)
        headers['Referer'] = f"{(headers.get('Referer') or SITE_URL).rstrip('/')}/"

        if not cookie_file:
            cookie_header = build_cookie_header(url, AGE_GATE_COOKIES)
            if cookie_header:
                headers['Cookie'] = cookie_header

        return headers


def extract_playback_info(url: str) -> dict[str, Any]:
    extractor = YouPornExtractor()
    info = extractor._extract_with_ytdlp(url)
    return dict(info or {})
