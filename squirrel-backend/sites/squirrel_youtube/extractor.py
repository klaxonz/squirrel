"""
YouTube video extractor.
"""
import logging
from datetime import datetime
from typing import Any

from sites.crawl import (
    SiteError,
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
)

from . import ytdlp_support as youtube_ytdlp_support

logger = logging.getLogger(__name__)
YOUTUBE_PLAYER_CLIENT = youtube_ytdlp_support.YOUTUBE_PLAYER_CLIENT
YOUTUBE_COOKIE_PLAYER_CLIENTS = youtube_ytdlp_support.YOUTUBE_COOKIE_PLAYER_CLIENTS


class YoutubeExtractor(YoutubeDLExtractorBase):
    """YouTube video extractor."""

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
        """Use yt-dlp to fetch YouTube video information."""
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

        except SiteError:
            # Typed errors (Auth/NotFound/Network/RateLimit/Parse) raised by
            # youtube_ytdlp_support.translate_ytdlp_error propagate unchanged;
            # the base extractor turns them into failure results.
            raise

    def _build_ytdlp_opts(self, url: str, queue_name: str | None = None) -> dict[str, Any]:
        """Build yt-dlp options."""
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
        """Process YouTube-specific information."""
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
