from __future__ import annotations

import logging
from typing import Any, List, Optional
from urllib.parse import quote

from .sign import fetch_play_data

logger = logging.getLogger(__name__)

SITE_SLUG = 'bilibili'


def _base_url(stream: dict) -> Optional[str]:
    return stream.get('baseUrl') or stream.get('base_url')


def _backup_urls(stream: dict) -> List[str]:
    backup_urls = stream.get('backupUrl') or stream.get('backup_url') or []
    if isinstance(backup_urls, list):
        return [str(url) for url in backup_urls if url]
    return []


def _proxy_stream_url(url: Optional[str], *, direct_playback: bool = False) -> Optional[str]:
    if not url:
        return None
    if direct_playback:
        return url
    return f'/api/video/proxy?domain=bilibili.com&url=' + quote(url, safe='')


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _codec_family_from_stream(stream: dict) -> Optional[str]:
    codecs = str(stream.get('codecs') or '').lower()
    if any(token in codecs for token in ('avc1', 'avc', 'h264')):
        return 'avc'
    if any(token in codecs for token in ('hev1', 'hvc1', 'hevc', 'h265')):
        return 'hevc'
    if any(token in codecs for token in ('av01', 'av1')):
        return 'av1'
    if any(token in codecs for token in ('vp09', 'vp9')):
        return 'vp9'

    codecid = _safe_int(stream.get('codecid'))
    if codecid == 7:
        return 'avc'
    if codecid == 12:
        return 'hevc'
    if codecid == 13:
        return 'av1'
    return None


def _video_stream_sort_key(stream: dict) -> tuple[int, int]:
    return (
        _safe_int(stream.get('height')),
        _safe_int(stream.get('bandwidth')),
    )


def _video_stream_group_sort_key(group: tuple[Optional[str], List[dict]]) -> tuple[int, int, int]:
    codec_family, streams = group
    best_height, best_bandwidth = _video_stream_sort_key(streams[0]) if streams else (0, 0)
    return (
        1 if codec_family == 'avc' else 0,
        best_height,
        best_bandwidth,
    )


def _group_video_streams_by_codec(video_streams: List[dict]) -> List[tuple[Optional[str], List[dict]]]:
    if not video_streams:
        return []

    grouped_by_codec: dict[Optional[str], List[dict]] = {}
    for stream in video_streams:
        codec_family = _codec_family_from_stream(stream)
        grouped_by_codec.setdefault(codec_family, []).append(stream)

    groups = [
        (codec_family, sorted(streams, key=_video_stream_sort_key, reverse=True))
        for codec_family, streams in grouped_by_codec.items()
    ]
    return sorted(groups, key=_video_stream_group_sort_key, reverse=True)


def get_dash_data(url: str) -> dict:
    play_data, _ = fetch_play_data(url, throttled=False)
    dash_data = play_data.get('dash') if isinstance(play_data, dict) else None
    if not dash_data:
        raise RuntimeError("Failed to fetch play data from bilibili")
    return dash_data


class BilibiliHandler:
    """Bilibili视频URL处理器，实现VideoUrlHandler Protocol"""
    
    domain = 'bilibili.com'

    def get_video_url(self, video: Any) -> dict:
        proxy_prefix_path = f"/api/video/proxy?domain=bilibili.com"

        dash_data = get_dash_data(video.url)

        best_video_url: Optional[str] = None
        best_audio_url: Optional[str] = None
        qualities: List[dict] = []

        video_streams = dash_data.get('video') or []
        audio_streams = dash_data.get('audio') or []

        if video_streams:
            video_stream_groups = _group_video_streams_by_codec(video_streams)
            quality_map = {
                16: 360,
                32: 480,
                48: 400,
                64: 720,
                74: 720,
                80: 1080,
                112: 1080,
                116: 1080,
                120: 2160,
                125: 2160,
                126: 2160,
                127: 4320,
            }

            for codec_family, grouped_streams in video_stream_groups:
                for index, stream in enumerate(grouped_streams):
                    bandwidth = stream.get('bandwidth')
                    vid = stream.get('id')
                    height = None
                    try:
                        qn = int(vid)
                        height = quality_map.get(qn)
                    except Exception:
                        height = None
                    if not height:
                        try:
                            height = int(stream.get('height') or 0) or None
                        except Exception:
                            height = None
                    label = f"{height}p" if height else (f"{int(bandwidth/1000)}kbps" if bandwidth else 'unknown')
                    value = f"{height}p" if height else (f"{int(bandwidth/1000)}kbps" if bandwidth else 'auto')
                    qualities.append({
                        'value': value,
                        'label': label,
                        'height': height,
                        'bandwidth': bandwidth,
                        'codec': codec_family,
                        'id': str(vid) if vid is not None else None,
                        'index': index,
                    })

            best_video_stream = max(video_streams, key=_video_stream_sort_key)
            best_video_url = _base_url(best_video_stream)

        if audio_streams:
            best_audio_stream = max(audio_streams, key=lambda x: x.get('bandwidth', 0))
            best_audio_url = _base_url(best_audio_stream)

            if not qualities:
                qualities = []
            else:
                def sort_key(q: dict):
                    return (q.get('height') or 0, q.get('bandwidth') or 0)

                height_counts: dict[tuple[str, int], int] = {}
                for q in qualities:
                    codec = str(q.get('codec') or '')
                    height = q.get('height') or 0
                    key = (codec, height)
                    height_counts[key] = height_counts.get(key, 0) + 1

                for q in qualities:
                    codec = str(q.get('codec') or '')
                    height = q.get('height')
                    if not height:
                        continue
                    if height_counts.get((codec, height), 0) > 1 and q.get('bandwidth'):
                        kbps = int((q.get('bandwidth') or 0) / 1000)
                        q['label'] = f"{height}p {kbps}kbps"
                        q['value'] = q['label']

                uniq: dict[str, dict] = {}
                for q in qualities:
                    key = f"{q.get('codec') or ''}|{q.get('height') or ''}|{q.get('bandwidth') or ''}"
                    uniq.setdefault(key, q)

                qualities = list(uniq.values())
                qualities = sorted(qualities, key=sort_key, reverse=True)


        return {
            'video_url': f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
            'audio_url': f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
            'mpd_url': f"/api/video/mpd?video_id={video.id}" if dash_data else None,
            'qualities': qualities or None,
        }
