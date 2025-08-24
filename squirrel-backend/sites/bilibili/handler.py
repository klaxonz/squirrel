import re
import json
import requests
from abc import ABC
from urllib.parse import quote
from core.exceptions.video_exceptions import VideoUrlExtractionError
from schemas.video.dto.video_dto import VideoUrlDto, QualityOptionDto
from sites.handler import VideoUrlHandler
from sites.handler_registry import register_handler
from models.video import Video
from botasaurus.request import request as brequest, Request
from utils.cookie import filter_cookies_to_query_string


@brequest(output=None, raise_exception=True, close_on_crash=True, create_error_logs=False, max_retry=10)
def _fetch_html(req: Request, link: str) -> str:
    cookies = filter_cookies_to_query_string(link)
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
        'Referer': link,
        'Accept-Language': 'en-US,en;q=0.9,zh-CN;q=0.8,zh;q=0.7',
        'Cookie': cookies
    }
    resp = req.get(link, headers=headers, timeout=20)
    resp.raise_for_status()
    return resp.text


def fetch_html(link: str) -> str:
    return _fetch_html(link)  # type: ignore


def extract_playinfo_from_html(html_content):
    match = re.search(r'window\.__playinfo__=(.*?)</script>', html_content)
    if not match:
        return None

    json_str = match.group(1).strip()
    if json_str.endswith(';'):
        json_str = json_str[:-1]

    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        return None


@register_handler
class BilibiliHandler(VideoUrlHandler, ABC):
    """Handler for Bilibili video URLs"""

    domain = 'bilibili.com'

    def supports_domain(self, domain: str) -> bool:
        return domain == 'bilibili.com'

    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            proxy_prefix_path = f"/api/video/proxy?domain=bilibili.com"

            html = fetch_html(video.url)

            data = extract_playinfo_from_html(html)
            if not data:
                raise VideoUrlExtractionError("Failed to extract playinfo data from HTML.")

            best_video_url = None
            best_audio_url = None
            qualities: list[QualityOptionDto] = []
            data = data.get('data', {})
            if 'dash' in data:
                dash_data = data['dash']
                if 'video' in dash_data:
                    video_urls = dash_data['video']
                    # Map Bilibili qn(id) to standard heights to avoid mis-reading width as height
                    QN_TO_HEIGHT = {
                        16: 360,
                        32: 480,
                        48: 400,   # legacy low bitrate
                        64: 720,
                        74: 720,   # 720P60
                        80: 1080,
                        112: 1080, # 1080P+ (higher bitrate)
                        116: 1080, # 1080P60
                        120: 2160, # 4K
                        125: 2160, # 4K HDR (if available)
                        126: 2160,
                        127: 4320, # 8K
                    }
                    for v in video_urls:
                        bw = v.get('bandwidth')
                        vid = v.get('id')
                        h = None
                        try:
                            qn = int(vid)
                            h = QN_TO_HEIGHT.get(qn)
                        except Exception:
                            h = None
                        # fallback to explicit height if mapping is missing
                        if not h:
                            try:
                                h = int(v.get('height') or 0) or None
                            except Exception:
                                h = None
                        label = f"{h}p" if h else (f"{int(bw/1000)}kbps" if bw else 'unknown')
                        # For frontend switching, use height label as value; keep qn in id
                        value = f"{h}p" if h else (f"{int(bw/1000)}kbps" if bw else 'auto')
                        qualities.append(QualityOptionDto(
                            value=value,
                            label=label,
                            height=h,
                            bandwidth=bw,
                            id=str(vid) if vid is not None else None
                        ))
                    # Pick best by bandwidth
                    if video_urls:
                        best_video_url = max(video_urls, key=lambda x: x.get('bandwidth', 0)).get('baseUrl')
                if 'audio' in dash_data:
                    audio_urls = dash_data['audio']
                    if audio_urls:
                        best_audio_url = max(audio_urls, key=lambda x: x.get('bandwidth', 0)).get('baseUrl')
            elif 'durl' in data or 'accept_quality' in data:
                # Handle non-DASH streams (durl) which may still have quality options
                if 'accept_quality' in data and 'accept_description' in data:
                    for quality_val, desc in zip(data['accept_quality'], data['accept_description']):
                        height_match = re.search(r'(\d+)P', desc)
                        height = int(height_match.group(1)) if height_match else None
                        qualities.append(QualityOptionDto(
                            value=str(quality_val),
                            label=desc,
                            height=height,
                            id=str(quality_val)
                        ))

                if 'durl' in data:
                    video_urls = data['durl']
                    best_video_url = video_urls[0]['url']

                if not qualities:
                    qualities = [QualityOptionDto(value='auto', label='自动')]

            # 去重并按分辨率从高到低排序，前端会在 DASH 模式用 auto
            if qualities:
                def key_fn(q: QualityOptionDto):
                    return (q.height or 0, q.bandwidth or 0)
                # unique by height label
                uniq = {}
                for q in qualities:
                    uniq[q.label] = q
                qualities = sorted(uniq.values(), key=key_fn, reverse=True)
                # 加上自动选项
                if not any(q.value == 'auto' for q in qualities):
                    qualities.insert(0, QualityOptionDto(value='auto', label='自动'))

            return VideoUrlDto(
                video_url=f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
                audio_url=f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
                mpd_url=f"/api/video/mpd?video_id={video.id}" if 'dash' in data else None,
                qualities=qualities or None
            )

        except requests.RequestException as e:
            raise VideoUrlExtractionError(f"Failed to fetch Bilibili video URL: {str(e)}")
        except KeyError as e:
            raise VideoUrlExtractionError(f"Missing expected data in Bilibili response: {str(e)}")
        except Exception as e:
            raise VideoUrlExtractionError(f"Unexpected error extracting Bilibili video URL: {str(e)}")
