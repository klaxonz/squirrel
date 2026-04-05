from __future__ import annotations

import logging
from typing import Any

from crawl import ParseError, VideoUrlHandler
from .mpd import _build_dash_representations, _extract_video_info, _proxy
from .playback_mapper import map_youtubei_result
from .youtubei_resolver import resolve_with_youtubei
from .video_id import extract_youtube_video_id

logger = logging.getLogger(__name__)


def _is_progressive_mp4(fmt: dict) -> bool:
    if not isinstance(fmt, dict):
        return False
    if not fmt.get('url'):
        return False
    if (fmt.get('ext') or '').lower() != 'mp4':
        return False

    vcodec = (fmt.get('vcodec') or '').lower()
    acodec = (fmt.get('acodec') or '').lower()
    return vcodec not in ('', 'none') and acodec not in ('', 'none')


def _codec_label(rep: dict) -> str | None:
    codec_family = (rep.get('codecFamily') or '').lower()
    if codec_family == 'av1':
        return 'AV1'
    if codec_family == 'vp9':
        return 'VP9'
    if codec_family == 'avc':
        return 'AVC'
    if codec_family == 'aac':
        return 'AAC'
    if codec_family == 'opus':
        return 'OPUS'
    return codec_family.upper() if codec_family else None


class YouTubeHandler:
    """YouTube视频URL处理器，实现VideoUrlHandler Protocol"""
    
    domain = 'youtube.com'

    def get_video_url(self, video: Any) -> dict:
        primary_error: Exception | None = None
        youtube_video_id = extract_youtube_video_id(getattr(video, 'url', '') or '')

        try:
            youtubei_result = resolve_with_youtubei(youtube_video_id or str(video.id))
            return map_youtubei_result(video.id, youtubei_result)
        except Exception as exc:
            primary_error = exc
            logger.warning('youtubei playback resolution failed, falling back to yt-dlp: %s', exc)

        fallback_payload = self._build_legacy_playback_payload(video)
        if fallback_payload:
            return fallback_payload

        raise ParseError(f'Unable to resolve YouTube playback for {video.url}: {primary_error}')

    def _build_legacy_playback_payload(self, video: Any) -> dict | None:
        info = _extract_video_info(video.url)
        if not info:
            return None

        mpd_payload = self._build_mpd_payload(video, info)
        if mpd_payload:
            return mpd_payload

        hls_payload = self._build_hls_payload(video, info)
        if hls_payload:
            return hls_payload

        progressive_payload = self._build_progressive_payload(video, info)
        if progressive_payload:
            return progressive_payload

        return None

    @staticmethod
    def _upstream_referer(video: Any, info: dict) -> str | None:
        return info.get('webpage_url') or getattr(video, 'url', None)

    def _build_mpd_payload(self, video: Any, info: dict) -> dict | None:
        video_reps = [
            r for r in _build_dash_representations(info)
            if isinstance(r.get('mime'), str) and r['kind'] == 'video' and r['mime'].startswith('video/')
        ]
        if not video_reps:
            logger.warning("YouTube 未提供可用的 DASH 视频流，尝试使用 HLS")
            return None

        video_sorted = sorted(
            video_reps,
            key=lambda r: (r.get('height') or 0, r.get('bandwidth') or 0),
            reverse=True
        )

        qualities = []
        for idx, rep in enumerate(video_sorted):
            height = rep.get('height')
            codec_label = _codec_label(rep)
            if height:
                label = f"{height}p {codec_label} (itag {rep['id']})" if codec_label else f"{height}p (itag {rep['id']})"
            else:
                label = f"{codec_label} (itag {rep['id']})" if codec_label else f"itag {rep['id']}"
            qualities.append({
                "value": str(rep['id']),
                "label": label,
                "height": int(height) if height else None,
                "bandwidth": int(rep['bandwidth']) if rep.get('bandwidth') else None,
                "codec": rep.get('codecFamily'),
                "id": str(rep['id']),
                "index": idx,
            })

        return {
            "mpd_url": f"/api/video/mpd?video_id={video.id}",
            "qualities": qualities or None,
        }

    def _build_progressive_payload(self, video: Any, info: dict) -> dict | None:
        formats = info.get('formats') or []
        progressive_formats = [
            fmt for fmt in formats
            if _is_progressive_mp4(fmt)
        ]
        if not progressive_formats:
            return None

        progressive_sorted = sorted(
            progressive_formats,
            key=lambda fmt: (fmt.get('height') or 0, fmt.get('tbr') or fmt.get('abr') or 0),
            reverse=True,
        )
        best = progressive_sorted[0]
        referer = self._upstream_referer(video, info)

        logger.warning("YouTube falling back to progressive MP4 stream")
        return {
            "video_url": _proxy(best['url'], referer=referer),
            "audio_url": None,
            "mpd_url": None,
            "qualities": None,
        }

    def _build_hls_payload(self, video: Any, info) -> dict | None:
        formats = info.get('formats') or []
        hls_formats = [
            fmt for fmt in formats
            if isinstance(fmt, dict) and (fmt.get('protocol') or '').lower().startswith('m3u8')
            and fmt.get('url')
        ]
        if not hls_formats:
            return None

        def score(fmt):
            fmt_note = (fmt.get('format_note') or '').lower()
            language_pref = fmt.get('language_preference') or 0
            height = fmt.get('height') or 0
            bitrate = fmt.get('tbr') or fmt.get('abr') or 0
            original = 1 if 'original' in fmt_note else 0
            return (original, language_pref, height, bitrate)

        best = max(hls_formats, key=score)
        referer = self._upstream_referer(video, info)
        proxied_url = _proxy(best['url'], referer=referer)
        lang = best.get('language')

        qualities = []
        filtered_formats = [
            fmt for fmt in hls_formats
            if (lang and fmt.get('language') == lang) or not lang
        ]
        filtered_formats.sort(key=lambda f: (f.get('height') or 0, f.get('tbr') or 0), reverse=True)
        for idx, fmt in enumerate(filtered_formats):
            height = fmt.get('height')
            value = fmt.get('format_id') or (f"{height}p" if height else fmt.get('format') or 'auto')
            label = fmt.get('format') or (f"{height}p" if height else str(value))
            bandwidth = fmt.get('tbr')
            if bandwidth:
                try:
                    bandwidth = int(float(bandwidth) * 1000)
                except Exception:
                    bandwidth = None
            qualities.append({
                "value": str(value),
                "label": label,
                "height": int(height) if height else None,
                "bandwidth": bandwidth,
                "id": fmt.get('format_id'),
                "index": idx
            })

        return {
            "video_url": proxied_url,
            "audio_url": None,
            "mpd_url": None,
            "qualities": qualities or None,
        }


