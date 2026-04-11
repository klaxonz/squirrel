"""
Pornhub视频提取器
"""
import html as html_lib
import logging
import re
import time
from datetime import datetime
from urllib.parse import urljoin, urlparse
from typing import Optional, Dict, Any

import requests
from yt_dlp import YoutubeDL

from crawl import (
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
    filter_cookies_to_query_string,
    resolve_cookie_file_path,
    get_http_headers,
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
)

logger = logging.getLogger(__name__)
SITE_DOMAIN = 'pornhub.com'
SITE_URL = f'https://www.{SITE_DOMAIN}'
DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
AGE_GATE_COOKIES = {
    'age_verified': '1',
    'accessAgeDisclaimerPH': '1',
    'accessAgeDisclaimerUK': '1',
    'accessPH': '1',
}
_META_THUMBNAIL_PATTERNS = (
    re.compile(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']', re.I),
    re.compile(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']', re.I),
    re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']', re.I),
)
_PAGE_FETCH_MAX_ATTEMPTS = 3
_PAGE_FETCH_RETRYABLE_STATUS_CODES = {403, 408, 425, 429, 500, 502, 503, 504}


class PornhubExtractor(YoutubeDLExtractorBase):
    """Pornhub视频提取器"""

    site_name = 'pornhub'
    supported_domains = ['pornhub.com']
    url_patterns = [
        'pornhub.com/view_video.php',
        'pornhub.com/embed/',
        'pornhub.com/video/'
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取Pornhub视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)

            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)

                if video_info:
                    self._process_pornhub_info(video_info, url)

                return video_info

        except Exception as e:
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}
            cookie_file = resolve_cookie_file_path(url)

            if 'unable to extract encoded url' in error_msg:
                redirect_target = self._resolve_redirect_target(url, cookie_file)
                if self._is_shorties_url(redirect_target):
                    context['blocked_reason_code'] = 'unsupported_short_redirect'
                    context['redirect_target'] = redirect_target
                    raise ParseError(f'暂不支持 Pornhub short 视频: {url}', context=context)

            if 'sign in' in error_msg or 'login' in error_msg or 'private' in error_msg:
                raise AuthError(f"需要登录访问: {url}", context=context)
            elif 'unavailable' in error_msg or 'removed' in error_msg or 'deleted' in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif any(kw in error_msg for kw in ['timeout', 'connection', 'network', 'closed file', 'i/o operation']):
                raise NetworkError(f"网络连接失败: {url}", context=context)
            else:
                logger.error(f"Pornhub视频信息提取失败: {url}", exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """构建yt-dlp选项"""
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

    def _process_pornhub_info(self, video_info: dict, source_url: Optional[str] = None) -> None:
        """处理Pornhub特定信息"""
        try:
            if 'timestamp' in video_info:
                video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
            self._normalize_thumbnail(video_info, source_url)
        except Exception as e:
            logger.warning(f"处理Pornhub特定信息失败: {e}")

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
        return bool(normalized) and '/plain/' in normalized and (
            'validto=' in normalized or 'hdnea=' in normalized
        )

    def _fetch_page_thumbnail_url(self, url: str) -> Optional[str]:
        page_url = str(url or '').strip()
        if not page_url:
            return None

        cookie_file = resolve_cookie_file_path(page_url)
        headers = self._build_ytdlp_headers(page_url, cookie_file)

        for attempt in range(1, _PAGE_FETCH_MAX_ATTEMPTS + 1):
            try:
                response = requests.get(
                    page_url,
                    headers=headers,
                    allow_redirects=True,
                    timeout=30,
                )
            except Exception as exc:
                logger.warning('Failed to fetch Pornhub page thumbnail metadata: %s', exc)
                return None

            if response.status_code == 200:
                for pattern in _META_THUMBNAIL_PATTERNS:
                    match = pattern.search(response.text)
                    if not match:
                        continue
                    thumbnail_url = html_lib.unescape(match.group(1).strip())
                    if thumbnail_url:
                        return thumbnail_url
                return None

            if (
                response.status_code in _PAGE_FETCH_RETRYABLE_STATUS_CODES
                and attempt < _PAGE_FETCH_MAX_ATTEMPTS
            ):
                time.sleep(min(5.0, 0.8 * attempt))
                continue

            return None

        return None

    def _build_ytdlp_headers(self, url: str, cookie_file: Optional[str]) -> Dict[str, str]:
        headers = get_http_headers(self.site_name, {
            'User-Agent': DEFAULT_USER_AGENT,
            'Referer': f'{SITE_URL}/',
            'Accept-Language': 'en-US,en;q=0.9',
        })
        headers.setdefault('User-Agent', DEFAULT_USER_AGENT)
        headers.setdefault('Accept-Language', 'en-US,en;q=0.9')
        headers.setdefault('Origin', SITE_URL)
        referer = (headers.get('Referer') or SITE_URL).rstrip('/')
        headers['Referer'] = f'{referer}/'

        if not cookie_file:
            headers['Cookie'] = self._build_cookie_header(url)

        return headers

    def _build_cookie_header(self, url: str) -> str:
        cookies = {}
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

    def _resolve_redirect_target(self, url: str, cookie_file: Optional[str]) -> Optional[str]:
        headers = self._build_ytdlp_headers(url, cookie_file)

        try:
            response = requests.get(
                url,
                headers=headers,
                allow_redirects=False,
                timeout=15,
            )
        except Exception as exc:
            logger.warning('Failed to inspect Pornhub redirect target: %s', exc)
            return None

        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get('location')
            if location:
                return urljoin(url, location)
        return response.url

    @staticmethod
    def _is_shorties_url(target_url: Optional[str]) -> bool:
        if not target_url:
            return False
        parsed = urlparse(target_url)
        return parsed.netloc.endswith(SITE_DOMAIN) and parsed.path.startswith('/shorties/')
