from __future__ import annotations

import logging
import re
from abc import ABC
from typing import List, Optional
from urllib.parse import quote

from crawl import (
    VideoUrlHandler,
    register_handler,
    IdExtractor,
    register_id_extractor,
    Video,
)
from .api_client import fetch_play_data

logger = logging.getLogger(__name__)

SITE_SLUG = 'bilibili'


def _base_url(stream: dict) -> Optional[str]:
    return stream.get('baseUrl') or stream.get('base_url')


def get_dash_data(url: str) -> dict:
    play_data, _ = fetch_play_data(url, throttled=False)
    dash_data = play_data.get('dash') if isinstance(play_data, dict) else None
    if not dash_data:
        raise RuntimeError("Failed to fetch play data from bilibili-api")
    return dash_data


@register_handler
class BilibiliHandler(VideoUrlHandler, ABC):
    domain = 'bilibili.com'

    def get_video_url(self, video: Video) -> dict:
        proxy_prefix_path = f"/api/video/proxy?domain=bilibili.com"

        dash_data = get_dash_data(video.url)

        best_video_url: Optional[str] = None
        best_audio_url: Optional[str] = None
        qualities: List[dict] = []
        id_to_index: dict[str, int] = {}

        video_streams = dash_data.get('video') or []
        audio_streams = dash_data.get('audio') or []

        if video_streams:
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

            filtered_streams = [
                v for v in video_streams
                if 'codecs' in v and any(x in v['codecs'] for x in ('avc', 'avc1', 'h264'))
            ] or video_streams

            index_meta: List[dict] = []

            for stream in filtered_streams:
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
                q = {
                    'value': value,
                    'label': label,
                    'height': height,
                    'bandwidth': bandwidth,
                    'id': str(vid) if vid is not None else None,
                }
                qualities.append(q)

                if vid is not None:
                    index_meta.append({
                        'id': str(vid),
                        'height': height or 0,
                        'bandwidth': bandwidth or 0,
                    })

            if index_meta:
                sorted_meta = sorted(index_meta, key=lambda m: (m['height'], m['bandwidth']))
                id_to_index = {m['id']: idx for idx, m in enumerate(sorted_meta)}

            best_video_stream = max(video_streams, key=lambda x: x.get('bandwidth', 0))
            best_video_url = _base_url(best_video_stream)

        if audio_streams:
            best_audio_stream = max(audio_streams, key=lambda x: x.get('bandwidth', 0))
            best_audio_url = _base_url(best_audio_stream)

        if not qualities:
            qualities = []
        else:
            def sort_key(q: dict):
                return (q.get('height') or 0, q.get('bandwidth') or 0)

            uniq: dict[str, dict] = {}
            for q in qualities:
                key = q['label']
                existing = uniq.get(key)
                if not existing:
                    uniq[key] = q
                else:
                    prev_id = existing.get('id')
                    new_id = q.get('id')
                    prev_idx = id_to_index.get(prev_id) if prev_id is not None else -1
                    new_idx = id_to_index.get(new_id) if new_id is not None else -1
                    if new_idx > prev_idx:
                        uniq[key] = q

            qualities = list(uniq.values())

            for q in qualities:
                vid = q.get('id')
                if vid is not None and vid in id_to_index:
                    q['index'] = id_to_index[vid]

            qualities = sorted(qualities, key=sort_key, reverse=True)

        return {
            'video_url': f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
            'audio_url': f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
            'mpd_url': f"/api/video/mpd?video_id={video.id}" if dash_data else None,
            'qualities': qualities or None,
        }


@register_id_extractor
class BilibiliIdExtractor(IdExtractor):
    domain = 'bilibili.com'

    def extract_id(self) -> str:
        pattern = r'BV[0-9A-Za-z]+'
        match = re.search(pattern, self.url)
        if match:
            return match.group(0)
        raise ValueError("Invalid url")


