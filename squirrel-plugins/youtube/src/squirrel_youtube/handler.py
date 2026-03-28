from __future__ import annotations

import logging
from typing import Any

from crawl import ParseError, VideoUrlHandler
from .mpd import _extract_video_info, _proxy, _format_to_rep

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
        info = _extract_video_info(video.url)
        if not info:
            raise ParseError(f'无法获取 YouTube 视频信息: {video.url}')

        mpd_payload = self._build_mpd_payload(video, info)
        if mpd_payload:
            return mpd_payload

        hls_payload = self._build_hls_payload(info)
        if hls_payload:
            return hls_payload

        progressive_payload = self._build_progressive_payload(info)
        if progressive_payload:
            return progressive_payload

        raise ParseError(f'未能获取到可用的 DASH、HLS 或 MP4 播放链接: {video.url}')

    def _build_mpd_payload(self, video: Any, info: dict) -> dict | None:
        kept_by_itag: dict[str, dict] = {}
        for fmt in info.get('formats') or []:
            rep = _format_to_rep(fmt)
            if not rep:
                continue
            itag = rep['id']
            if itag not in kept_by_itag:
                kept_by_itag[itag] = rep

        video_reps = [
            r for r in kept_by_itag.values()
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
                "id": str(rep['id']),
                "index": idx,
            })

        return {
            "mpd_url": f"/api/video/mpd?video_id={video.id}",
            "qualities": qualities or None,
        }

    def _build_progressive_payload(self, info: dict) -> dict | None:
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

        logger.warning("YouTube falling back to progressive MP4 stream")
        return {
            "video_url": _proxy(best['url']),
            "audio_url": None,
            "mpd_url": None,
            "qualities": None,
        }

    def _build_hls_payload(self, info) -> dict | None:
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
        proxied_url = _proxy(best['url'])
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


