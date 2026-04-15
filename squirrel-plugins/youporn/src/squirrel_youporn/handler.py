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

        if self._prefer_progressive_for_desktop(video):
            progressive_url = self._select_progressive_url(formats)
            if progressive_url:
                return {
                    'stream_type': 'progressive',
                    'video_url': progressive_url,
                    'audio_url': None,
                    'supports_manual_quality': False,
                }
            raise ParseError(
                'Desktop playback requires a direct YouPorn stream, but no progressive MP4 format was returned',
                context={'url': video_url},
            )

        hls_url = self._select_hls_url(formats)
        if hls_url:
            qualities = self._build_hls_qualities(formats)
            return {
                'stream_type': 'hls',
                'video_url': self._build_proxy_url(hls_url),
                'audio_url': None,
                'qualities': qualities or None,
                'default_quality_id': qualities[0]['id'] if qualities else None,
                'supports_manual_quality': len(qualities) > 1,
            }

        progressive_url = self._select_progressive_url(formats)
        if progressive_url:
            return {
                'stream_type': 'progressive',
                'video_url': progressive_url,
                'audio_url': None,
                'supports_manual_quality': False,
            }

        raise ParseError('No supported YouPorn playback format was found', context={'url': video_url})

    @staticmethod
    def _prefer_progressive_for_desktop(video: Any) -> bool:
        client_type = str(getattr(video, 'client_type', '') or '').strip().lower()
        direct_playback = bool(getattr(video, 'direct_playback', False))
        return client_type == 'desktop' or direct_playback

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

    def _build_hls_qualities(self, formats: Iterable[Dict[str, Any]]) -> list[dict]:
        qualities: list[dict] = []
        for item in formats:
            protocol = str(item.get('protocol') or '').lower()
            candidate = str(item.get('manifest_url') or item.get('url') or '').strip()
            if not candidate:
                continue
            if 'm3u8' not in protocol and not candidate.endswith('.m3u8'):
                continue

            format_id = str(item.get('format_id') or '').strip() or None
            height = self._safe_int(item.get('height'))
            bandwidth = self._safe_bandwidth(item.get('tbr'))
            codec = self._codec_family_from_format(item)
            label = f'{height}p' if height else (format_id or 'HLS')
            quality_id = format_id or f'hls:{height or 0}:{bandwidth or 0}:{codec or "unknown"}'
            qualities.append({
                'value': quality_id,
                'label': label,
                'height': height or None,
                'bandwidth': bandwidth,
                'codec': codec,
                'id': quality_id,
            })

        deduped: dict[str, dict] = {}
        for item in sorted(qualities, key=self._quality_sort_key, reverse=True):
            deduped.setdefault(str(item['id']), item)
        return list(deduped.values())

    @staticmethod
    def _quality_sort_key(item: Dict[str, Any]) -> tuple[int, int]:
        return int(item.get('height') or 0), int(item.get('bandwidth') or 0)

    @staticmethod
    def _safe_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _safe_bandwidth(value: Any) -> Optional[int]:
        try:
            parsed = float(value or 0.0)
        except (TypeError, ValueError):
            return None
        return int(parsed * 1000) if parsed > 0 else None

    @staticmethod
    def _codec_family_from_format(item: Dict[str, Any]) -> Optional[str]:
        codec = str(item.get('vcodec') or '').lower()
        if not codec or codec == 'none':
            return None
        if 'av01' in codec or 'av1' in codec:
            return 'av1'
        if 'vp09' in codec or 'vp9' in codec:
            return 'vp9'
        if 'avc1' in codec or 'avc' in codec or 'h264' in codec:
            return 'avc'
        if 'hev1' in codec or 'hvc1' in codec or 'hevc' in codec or 'h265' in codec:
            return 'hevc'
        return codec

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
