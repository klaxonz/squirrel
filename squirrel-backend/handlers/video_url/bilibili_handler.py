from urllib.parse import quote


import requests
from botasaurus_requests import Request

from dto.video_dto import VideoUrlDto
from handlers.video_url.base import VideoUrlHandler, VideoUrlExtractionError
from models.video import Video
from utils.cookie import filter_cookies_to_query_string
from downloader.id_extractor import extract_bilibili_id
from subscribe.platforms.bilibili.sign import sign
from botasaurus.request import request as brequest, Request
import json
import re



@brequest(output=None, raise_exception=True, close_on_crash=True, create_error_logs=False, max_retry=10)
def _fetch_html(req: Request, link: str) -> str:
    resp = req.get(link, timeout=20)
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


class BilibiliHandler(VideoUrlHandler):
    """Handler for Bilibili video URLs"""

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

            if 'dash' in data.get('data', {}):
                dash_data = data['dash']
                if 'video' in dash_data:
                    video_urls = dash_data['video']
                    best_video_url = max(video_urls, key=lambda x: x['bandwidth'])['baseUrl']
                if 'audio' in dash_data:
                    audio_urls = dash_data['audio']
                    best_audio_url = max(audio_urls, key=lambda x: x['bandwidth'])['baseUrl']
            elif 'durl' in data.get('data', {}):
                video_urls = data['durl']
                best_video_url = video_urls[0]['url']

            return VideoUrlDto(
                video_url=f"{proxy_prefix_path}&url=" + quote(best_video_url) if best_video_url else None,
                audio_url=f"{proxy_prefix_path}&url=" + quote(best_audio_url) if best_audio_url else None,
                mpd_url=f"{proxy_prefix_path}&mpd="
            )

        except requests.RequestException as e:
            raise VideoUrlExtractionError(f"Failed to fetch Bilibili video URL: {str(e)}")
        except KeyError as e:
            raise VideoUrlExtractionError(f"Missing expected data in Bilibili response: {str(e)}")
        except Exception as e:
            raise VideoUrlExtractionError(f"Unexpected error extracting Bilibili video URL: {str(e)}")
