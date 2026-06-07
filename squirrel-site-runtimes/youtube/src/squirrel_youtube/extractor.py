"""
YouTube视频提取器
"""
import logging
from datetime import datetime
from typing import Any

from crawl import (
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
    RateLimitError,
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
)

from . import ytdlp_support as youtube_ytdlp_support

logger = logging.getLogger(__name__)
YOUTUBE_PLAYER_CLIENT = youtube_ytdlp_support.YOUTUBE_PLAYER_CLIENT
YOUTUBE_COOKIE_PLAYER_CLIENTS = youtube_ytdlp_support.YOUTUBE_COOKIE_PLAYER_CLIENTS


class YoutubeExtractor(YoutubeDLExtractorBase):
    """YouTube视频提取器"""

    site_name = "youtube"
    supported_domains = ["youtube.com", "youtu.be"]
    url_patterns = [
        "youtube.com/watch",
        "youtube.com/shorts",
        "youtu.be/",
        "m.youtube.com"
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: str | None = None) -> dict[str, Any] | None:
        """使用yt-dlp获取YouTube视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            video_info = youtube_ytdlp_support.extract_info(
                url,
                ydl_opts,
                process=False,
            )

            if video_info:
                self._process_youtube_info(video_info)

            return video_info

        except Exception as e:  # SDK boundary — translate yt-dlp errors to domain types
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if "sign in" in error_msg or "private video" in error_msg or "members-only" in error_msg:
                raise AuthError(f"需要登录或为私有视频: {url}", context=context)
            elif "video unavailable" in error_msg or "removed" in error_msg or "deleted" in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif any(kw in error_msg for kw in ["timeout", "timed out", "connection", "network", "closed file", "i/o operation"]):
                raise NetworkError(f"网络连接失败: {url}", context=context)
            elif any(kw in error_msg for kw in ["too many requests", "rate limit", "429"]):
                raise RateLimitError(f"请求频率过高: {url}", context=context)
            else:
                logger.error("YouTube视频信息提取失败: %s", url, exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _build_ytdlp_opts(self, url: str, queue_name: str | None = None) -> dict[str, Any]:
        """构建yt-dlp选项"""
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
            "extractor_args": {
                "youtube": {
                    "player_client": [YOUTUBE_PLAYER_CLIENT],
                }
            },
        }

        youtube_ytdlp_support.apply_youtube_player_strategy(url, ydl_opts)

        return apply_ytdlp_rate_limit(self.site_name, ydl_opts)

    def _process_youtube_info(self, video_info: dict) -> None:
        """处理YouTube特定信息"""
        try:
            publish_date = self._resolve_publish_date(video_info)
            if publish_date is not None:
                video_info["publish_date"] = publish_date
        except (ValueError, TypeError) as e:
            logger.warning("处理YouTube特定信息失败: %s", e)

    def _resolve_publish_date(self, video_info: dict[str, Any]) -> datetime | None:
        """Resolve the most accurate publish date from yt-dlp metadata."""
        for timestamp_key in ("release_timestamp", "timestamp"):
            timestamp = video_info.get(timestamp_key)
            if timestamp:
                return datetime.fromtimestamp(timestamp)

        for date_key in ("release_date", "upload_date"):
            date_text = video_info.get(date_key)
            if isinstance(date_text, str) and date_text:
                try:
                    return datetime.strptime(date_text, "%Y%m%d")
                except ValueError:
                    continue

        return None
