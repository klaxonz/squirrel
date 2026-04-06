from __future__ import annotations

from typing import Any, Dict, Iterable, Optional
from urllib.parse import quote

from crawl import ParseError

from .extractor import extract_playback_info


class YouPornHandler:
    """Resolve YouPorn playback URLs using yt-dlp metadata."""

    domain = 'youporn.com'

    def get_video_url(self, video: Any) -> dict:
        video_url = str(getattr(video, 'url', '') or '').strip()
        if not video_url:
            raise ParseError('Missing video url for YouPorn playback resolution', context={'video': repr(video)})

        info = extract_playback_info(video_url)
        formats = list(info.get('formats') or [])
        if not formats:
            raise ParseError('No YouPorn playback formats were returned', context={'url': video_url})

        hls_url = self._select_hls_url(formats)
        if hls_url:
            return {
                'video_url': self._build_proxy_url(hls_url),
                'audio_url': None,
            }

        progressive_url = self._select_progressive_url(formats)
        if progressive_url:
            return {
                'video_url': progressive_url,
                'audio_url': None,
            }

        raise ParseError('No supported YouPorn playback format was found', context={'url': video_url})

    def _build_proxy_url(self, url: str) -> str:
        return f'/api/video/proxy?domain={self.domain}&url={quote(url)}'

    def _select_hls_url(self, formats: Iterable[Dict[str, Any]]) -> Optional[str]:
        hls_formats = []
        for item in formats:
            protocol = str(item.get('protocol') or '').lower()
            candidate = str(item.get('manifest_url') or item.get('url') or '').strip()
            if not candidate:
                continue
            if 'm3u8' in protocol or candidate.endswith('.m3u8'):
                hls_formats.append(item)

        if not hls_formats:
            return None

        best = max(hls_formats, key=self._format_sort_key)
        return str(best.get('manifest_url') or best.get('url') or '').strip() or None

    def _select_progressive_url(self, formats: Iterable[Dict[str, Any]]) -> Optional[str]:
        progressive_formats = []
        for item in formats:
            protocol = str(item.get('protocol') or '').lower()
            candidate = str(item.get('url') or '').strip()
            if not candidate:
                continue
            if protocol in {'https', 'http'} and 'm3u8' not in candidate:
                progressive_formats.append(item)

        if not progressive_formats:
            return None

        best = max(progressive_formats, key=self._format_sort_key)
        return str(best.get('url') or '').strip() or None

    @staticmethod
    def _format_sort_key(item: Dict[str, Any]) -> tuple[int, float]:
        height = item.get('height')
        tbr = item.get('tbr')
        try:
            normalized_height = int(height or 0)
        except (TypeError, ValueError):
            normalized_height = 0
        try:
            normalized_tbr = float(tbr or 0.0)
        except (TypeError, ValueError):
            normalized_tbr = 0.0
        return normalized_height, normalized_tbr
