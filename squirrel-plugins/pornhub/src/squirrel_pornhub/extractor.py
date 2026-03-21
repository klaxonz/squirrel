"""
Pornhub视频提取器
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from yt_dlp import YoutubeDL

from crawl import (
    YoutubeDLExtractorBase,
    register_extractor,
    apply_ytdlp_rate_limit,
    filter_cookies_to_query_string,
    resolve_cookie_file_path,
    get_http_headers,
    get_proxy_config_registry,
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


@register_extractor('pornhub', ['pornhub.com'])
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
                    self._process_pornhub_info(video_info)

                return video_info

        except Exception as e:
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

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

    def _process_pornhub_info(self, video_info: dict) -> None:
        """处理Pornhub特定信息"""
        try:
            if 'timestamp' in video_info:
                video_info['publish_date'] = datetime.fromtimestamp(video_info['timestamp'])
        except Exception as e:
            logger.warning(f"处理Pornhub特定信息失败: {e}")

    def _build_ytdlp_headers(self, url: str, cookie_file: Optional[str]) -> Dict[str, str]:
        proxy_config_registry = get_proxy_config_registry()
        provider_cls = proxy_config_registry.get(SITE_DOMAIN)
        base_headers = provider_cls.get_site_headers() if provider_cls else {}
        headers = get_http_headers(self.site_name, base_headers)
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
