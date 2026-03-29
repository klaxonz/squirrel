"""
YouTube视频提取器
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

from crawl import (
    YoutubeDLExtractorBase,
    apply_ytdlp_rate_limit,
    AuthError,
    NetworkError,
    NotFoundError,
    ParseError,
)
try:
    from . import ytdlp_support as youtube_ytdlp_support
except ImportError:  # pragma: no cover - fallback for direct module loading
    import importlib.util
    import sys
    from pathlib import Path

    _HELPER_PATH = Path(__file__).with_name('ytdlp_support.py')
    _HELPER_SPEC = importlib.util.spec_from_file_location('_youtube_ytdlp_support', _HELPER_PATH)
    youtube_ytdlp_support = importlib.util.module_from_spec(_HELPER_SPEC)
    assert _HELPER_SPEC is not None and _HELPER_SPEC.loader is not None
    sys.modules['_youtube_ytdlp_support'] = youtube_ytdlp_support
    _HELPER_SPEC.loader.exec_module(youtube_ytdlp_support)

logger = logging.getLogger(__name__)
YOUTUBE_PLAYER_CLIENT = youtube_ytdlp_support.YOUTUBE_PLAYER_CLIENT
YOUTUBE_COOKIE_PLAYER_CLIENTS = youtube_ytdlp_support.YOUTUBE_COOKIE_PLAYER_CLIENTS


class YoutubeExtractor(YoutubeDLExtractorBase):
    """YouTube视频提取器"""

    site_name = 'youtube'
    supported_domains = ['youtube.com', 'youtu.be']
    url_patterns = [
        'youtube.com/watch',
        'youtube.com/shorts',
        'youtu.be/',
        'm.youtube.com'
    ]

    def __init__(self):
        super().__init__(self.site_name, self.supported_domains)

    def _extract_with_ytdlp(self, url: str, queue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """使用yt-dlp获取YouTube视频信息"""
        try:
            ydl_opts = self._build_ytdlp_opts(url, queue_name)
            video_info = youtube_ytdlp_support.extract_info_with_player_responses(
                url,
                ydl_opts,
                process=False,
            )

            if video_info:
                self._process_youtube_info(video_info)

            return video_info

        except Exception as e:
            error_msg = str(e).lower()
            context = {"url": url, "original_error": str(e)}

            if 'sign in' in error_msg or 'private video' in error_msg or 'members-only' in error_msg:
                raise AuthError(f"需要登录或为私有视频: {url}", context=context)
            elif 'video unavailable' in error_msg or 'removed' in error_msg or 'deleted' in error_msg:
                raise NotFoundError(f"视频不存在或已删除: {url}", context=context)
            elif any(kw in error_msg for kw in ['timeout', 'connection', 'network', 'closed file', 'i/o operation']):
                raise NetworkError(f"网络连接失败: {url}", context=context)
            else:
                logger.error(f"YouTube视频信息提取失败: {url}", exc_info=True)
                raise ParseError(f"视频信息提取失败: {str(e)}", context=context)

    def _build_ytdlp_opts(self, url: str, queue_name: Optional[str] = None) -> Dict[str, Any]:
        """构建yt-dlp选项"""
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
            'extractor_args': {
                'youtube': {
                    'player_client': [YOUTUBE_PLAYER_CLIENT],
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
                video_info['publish_date'] = publish_date
        except Exception as e:
            logger.warning(f"处理YouTube特定信息失败: {e}")

    def _resolve_publish_date(self, video_info: Dict[str, Any]) -> Optional[datetime]:
        """Resolve the most accurate publish date from yt-dlp metadata."""
        for timestamp_key in ('release_timestamp', 'timestamp'):
            timestamp = video_info.get(timestamp_key)
            if timestamp:
                return datetime.fromtimestamp(timestamp)

        for date_key in ('release_date', 'upload_date'):
            date_text = video_info.get(date_key)
            if isinstance(date_text, str) and date_text:
                try:
                    return datetime.strptime(date_text, '%Y%m%d')
                except ValueError:
                    continue

        return None
