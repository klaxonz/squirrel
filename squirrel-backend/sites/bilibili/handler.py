import re
import json
import requests
from abc import ABC
from urllib.parse import quote
from core.exceptions.video_exceptions import VideoUrlExtractionError
from schemas.video.dto.video_dto import VideoUrlDto
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
            data = data.get('data', {})
            if 'dash' in data:
                dash_data = data['dash']
                if 'video' in dash_data:
                    video_urls = dash_data['video']
                    best_video_url = max(video_urls, key=lambda x: x['bandwidth'])['baseUrl']
                if 'audio' in dash_data:
                    audio_urls = dash_data['audio']
                    best_audio_url = max(audio_urls, key=lambda x: x['bandwidth'])['baseUrl']
            elif 'durl' in data:
                video_urls = data['durl']
                best_video_url = video_urls[0]['url']

            return VideoUrlDto(
                video_url=f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
                audio_url=f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
                mpd_url=f"/api/video/mpd?video_id={video.id}" if 'dash' in data else None
            )

        except requests.RequestException as e:
            raise VideoUrlExtractionError(f"Failed to fetch Bilibili video URL: {str(e)}")
        except KeyError as e:
            raise VideoUrlExtractionError(f"Missing expected data in Bilibili response: {str(e)}")
        except Exception as e:
            raise VideoUrlExtractionError(f"Unexpected error extracting Bilibili video URL: {str(e)}")
