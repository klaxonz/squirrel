from __future__ import annotations

import html as html_lib
import logging
import re
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
    filter_cookies_to_query_string,
    get_http_headers,
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
_META_THUMBNAIL_PATTERNS = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.I),
)


class YouPornExtractor(YoutubeDLExtractorBase):
    """YouPorn video extractor backed by yt-dlp."""

    site_name = 'youporn'
    supported_domains = ['youporn.com']
    url_patterns = ['youporn.com/watch/']

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if YoutubeDL is None:
            raise ParseError('yt-dlp is not installed', context={'url': url, 'site_name': self.site_name})

        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)
                if video_info:
                    self._process_youporn_info(video_info, url)
                return video_info
        except Exception as exc:
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

    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        cookie_file = resolve_cookie_file_path(url)
        headers = self._build_ytdlp_headers(url, cookie_file)
        ydl_opts: Dict[str, Any] = {
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

    def _process_youporn_info(self, video_info: Dict[str, Any], source_url: Optional[str] = None) -> None:
        try:
            timestamp = video_info.get('timestamp')
            if timestamp:
                video_info['publish_date'] = datetime.fromtimestamp(timestamp)
            self._normalize_thumbnail(video_info, source_url)
        except Exception as exc:
            logger.warning('Failed to process YouPorn video info: %s', exc)

    def _normalize_thumbnail(self, video_info: Dict[str, Any], source_url: Optional[str]) -> None:
        thumbnail_url = str(video_info.get('thumbnail') or '').strip()
        if not self._looks_like_expiring_preview_thumbnail(thumbnail_url):
            return

        fresh_thumbnail_url = self._fetch_page_thumbnail_url(source_url or str(video_info.get('webpage_url') or '').strip())
        if not fresh_thumbnail_url:
            return

        video_info['thumbnail'] = fresh_thumbnail_url
        if isinstance(video_info.get('thumbnails'), list) and video_info['thumbnails']:
            video_info['thumbnails'][0]['url'] = fresh_thumbnail_url

    @staticmethod
    def _looks_like_expiring_preview_thumbnail(url: str) -> bool:
        normalized = str(url or '').strip().lower()
        return bool(normalized) and '.mp4/plain/' in normalized and 'validto=' in normalized

    def _fetch_page_thumbnail_url(self, url: str) -> Optional[str]:
        page_url = str(url or '').strip()
        if not page_url:
            return None

        cookie_file = resolve_cookie_file_path(page_url)
        headers = self._build_ytdlp_headers(page_url, cookie_file)

        try:
            response = httpx.get(page_url, headers=headers, timeout=30.0, follow_redirects=True)
        except Exception as exc:
            logger.warning('Failed to fetch YouPorn page thumbnail metadata: %s', exc)
            return None

        if response.status_code != 200:
            return None

        html_text = response.text
        for pattern in _META_THUMBNAIL_PATTERNS:
            match = pattern.search(html_text)
            if not match:
                continue
            thumbnail_url = html_lib.unescape(match.group(1).strip())
            if thumbnail_url:
                return thumbnail_url

        return None

    def _build_ytdlp_headers(self, url: str, cookie_file: Optional[str]) -> Dict[str, str]:
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
            cookie_header = self._build_cookie_header(url)
            if cookie_header:
                headers['Cookie'] = cookie_header

        return headers

    def _build_cookie_header(self, url: str) -> str:
        cookies: Dict[str, str] = {}
        raw_cookie_header = filter_cookies_to_query_string(url)

        for segment in raw_cookie_header.split(';'):
            item = segment.strip()
            if not item or '=' not in item:
                continue
            name, value = item.split('=', 1)
            cookies[name.strip()] = value.strip()

        for name, value in AGE_GATE_COOKIES.items():
            cookies.setdefault(name, value)

        return '; '.join(f'{name}={value}' for name, value in cookies.items())


def extract_playback_info(url: str) -> Dict[str, Any]:
    extractor = YouPornExtractor()
    info = extractor._extract_with_ytdlp(url)
    return dict(info or {})
