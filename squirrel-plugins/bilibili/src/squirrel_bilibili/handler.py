from __future__ import annotations

import json
import re
from abc import ABC
from typing import List, Optional
from urllib.parse import quote

import requests
from botasaurus.request import request as brequest, Request

from crawl import (
    VideoUrlHandler,
    register_handler,
    IdExtractor,
    register_id_extractor,
    Video,
    filter_cookies_to_query_string,
)


@brequest(output=None, raise_exception=True, close_on_crash=True, create_error_logs=False, max_retry=10)
def _fetch_html(req: Request, link: str) -> str:
    cookies = filter_cookies_to_query_string(link)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': link,
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Cookie': cookies,
    }
    resp = req.get(link, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def fetch_html(link: str) -> str:
    return _fetch_html(link)  # type: ignore


def extract_playinfo_from_html(html_content: str):
    match = re.search(r'window\.__playinfo__=(.*?)</script>', html_content)
    if not match:
        return None

    json_str = match.group(1).strip()
    if json_str.endswith(';'):
        json_str = json_str[:-1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return None


@register_handler
class BilibiliHandler(VideoUrlHandler, ABC):
    domain = 'bilibili.com'

    def get_video_url(self, video: Video) -> dict:
        proxy_prefix_path = f"/api/video/proxy?domain=bilibili.com"

        html = fetch_html(video.url)
        data = extract_playinfo_from_html(html)
        if not data:
            raise RuntimeError("Failed to extract playinfo data from HTML")

        best_video_url: Optional[str] = None
        best_audio_url: Optional[str] = None
        qualities: List[dict] = []
        payload = data.get('data', {})

        if 'dash' in payload:
            dash_data = payload['dash']
            if 'video' in dash_data:
                video_streams = dash_data['video']
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
                for stream in video_streams:
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
                        'id': str(vid) if vid is not None else None,
                    })

                if video_streams:
                    best_video_url = max(video_streams, key=lambda x: x.get('bandwidth', 0)).get('baseUrl')

            if 'audio' in dash_data:
                audio_streams = dash_data['audio']
                if audio_streams:
                    best_audio_url = max(audio_streams, key=lambda x: x.get('bandwidth', 0)).get('baseUrl')

        if not qualities:
            qualities = [{'value': 'auto', 'label': '自动'}]
        else:
            def sort_key(q: dict):
                return (q.get('height') or 0, q.get('bandwidth') or 0)

            uniq = {}
            for q in qualities:
                uniq[q['label']] = q
            qualities = sorted(uniq.values(), key=sort_key, reverse=True)
            if not any(q['value'] == 'auto' for q in qualities):
                qualities.insert(0, {'value': 'auto', 'label': '自动'})

        return {
            'video_url': f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
            'audio_url': f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
            'mpd_url': f"/api/video/mpd?video_id={video.id}" if payload.get('dash') else None,
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



