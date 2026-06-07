"""
Pornhub视频提取器
"""
import logging
from datetime import datetime
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
    build_cookie_header,
    fetch_page_thumbnail_url,
    get_http_headers,
    normalize_thumbnail,
    resolve_cookie_file_path,
)
from yt_dlp import YoutubeDL

logger = logging.getLogger(__name__)
SITE_DOMAIN = "pornhub.com"
SITE_URL = f"https://www.{SITE_DOMAIN}"
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
AGE_GATE_COOKIES = {
    "age_verified": "1",
    "accessAgeDisclaimerPH": "1",
    "accessAgeDisclaimerUK": "1",
    "accessPH": "1",
}


class PornhubExtractor(YoutubeDLExtractorBase):
    """Pornhub视频提取器"""

    site_name = "pornhub"
    supported_domains = ["pornhub.com"]
    url_patterns = [
        "pornhub.com/view_video.php",
        "pornhub.com/embed/",
        "pornhub.com/video/"
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """使用yt-dlp获取Pornhub视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)

            with YoutubeDL(ydl_opts) as ydl:
                video_info = ydl.extract_info(url, download=False)

                if video_info:
                    self._process_pornhub_info(video_info, url)

                return video_info

        except Exception as e:  # SDK boundary — translate yt-dlp errors to domain types
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}
            cookie_file = resolve_cookie_file_path(url)

            if "unable to extract encoded url" in error_msg:
                redirect_target = self._resolve_redirect_target(url, cookie_file)
                if self._is_shorties_url(redirect_target):
                    context["blocked_reason_code"] = "unsupported_short_redirect"
                    context["redirect_target"] = redirect_target
                    raise ParseError(f"暂不支持 Pornhub short 视频: {url}", context=context)

            if "sign in" in error_msg or "login" in error_msg or "private" in error_msg:
                raise AuthError(f"需要登录访问: {url}", context=context)
            elif "unavailable" in error_msg or "removed" in error_msg or "deleted" in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif any(kw in error_msg for kw in ["timeout", "connection", "network", "closed file", "i/o operation"]):
                raise NetworkError(f"网络连接失败: {url}", context=context)
            elif any(kw in error_msg for kw in ["too many requests", "rate limit", "429"]):
                raise RateLimitError(f"请求频率过高: {url}", context=context)
            else:
                logger.error("Pornhub视频信息提取失败: %s", url, exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _build_ytdlp_opts(self, url: str, queue_name: str | None = None) -> dict[str, Any]:
        """构建yt-dlp选项"""
        cookie_file = resolve_cookie_file_path(url)
        headers = self._build_ytdlp_headers(url, cookie_file)
        ydl_opts: dict[str, Any] = {
            "quiet": True,
            "skip_download": True,
            "socket_timeout": 30,
            "retries": 5,
            "extractor_retries": 3,
            "fragment_retries": 5,
            "file_access_retries": 3,
            "ignoreerrors": False,
            "noprogress": True,
            "noplaylist": True,
            "http_headers": headers,
        }

        if cookie_file:
            ydl_opts["cookiefile"] = cookie_file

        return apply_ytdlp_rate_limit(self.site_name, ydl_opts)

    def _process_pornhub_info(self, video_info: dict, source_url: str | None = None) -> None:
        """处理Pornhub特定信息"""
        try:
            if "timestamp" in video_info:
                video_info["publish_date"] = datetime.fromtimestamp(video_info["timestamp"])
            normalize_thumbnail(video_info, source_url, self._fetch_page_thumbnail_url)
        except (ValueError, TypeError) as e:
            logger.warning("处理Pornhub特定信息失败: %s", e)

    def _fetch_page_thumbnail_url(self, url: str) -> str | None:
        cookie_file = resolve_cookie_file_path(url)
        return fetch_page_thumbnail_url(url, cookie_file, self._build_ytdlp_headers)

    def _build_ytdlp_headers(self, url: str, cookie_file: str | None) -> dict[str, str]:
        headers = get_http_headers(self.site_name, {
            "User-Agent": DEFAULT_USER_AGENT,
            "Referer": f"{SITE_URL}/",
            "Accept-Language": "en-US,en;q=0.9",
        })
        headers.setdefault("User-Agent", DEFAULT_USER_AGENT)
        headers.setdefault("Accept-Language", "en-US,en;q=0.9")
        headers.setdefault("Origin", SITE_URL)
        referer = (headers.get("Referer") or SITE_URL).rstrip("/")
        headers["Referer"] = f"{referer}/"

        if not cookie_file:
            headers["Cookie"] = build_cookie_header(url, AGE_GATE_COOKIES)

        return headers

    def _resolve_redirect_target(self, url: str, cookie_file: str | None) -> str | None:
        headers = self._build_ytdlp_headers(url, cookie_file)

        try:
            response = httpx.get(
                url,
                headers=headers,
                follow_redirects=False,
                timeout=15,
            )
        except Exception as exc:  # HTTP I/O boundary — httpx may raise various transport errors
            logger.warning("Failed to inspect Pornhub redirect target: %s", exc)
            return None

        if response.status_code in (301, 302, 303, 307, 308):
            location = response.headers.get("location")
            if location:
                return urljoin(url, location)
        return str(response.url)

    @staticmethod
    def _is_shorties_url(target_url: str | None) -> bool:
        if not target_url:
            return False
        parsed = urlparse(target_url)
        return parsed.netloc.endswith(SITE_DOMAIN) and parsed.path.startswith("/shorties/")
