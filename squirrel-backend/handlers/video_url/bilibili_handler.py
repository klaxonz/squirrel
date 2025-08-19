from urllib.parse import quote
import requests
from dto.video_dto import VideoUrlDto
from handlers.video_url.base import VideoUrlHandler, VideoUrlExtractionError
from models.video import Video
from utils.cookie import filter_cookies_to_query_string
from downloader.id_extractor import extract_bilibili_id
from subscribe.platforms.bilibili.sign import sign


class BilibiliHandler(VideoUrlHandler):
    """Handler for Bilibili video URLs"""

    def supports_domain(self, domain: str) -> bool:
        return domain == 'bilibili.com'

    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            proxy_prefix_path = f"/api/video/proxy?domain=bilibili.com"

            cookies = filter_cookies_to_query_string("https://www.bilibili.com")
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Referer': 'https://www.bilibili.com',
                'Origin': 'https://www.bilibili.com',
                'Accept-Language': 'zh-CN,zh;q=0.9',
                'Cookie': cookies
            }

            bv_id = extract_bilibili_id(video.url)
            req_url = f'https://api.bilibili.com/x/web-interface/view?bvid={bv_id}'
            resp = requests.get(req_url, headers=headers)
            resp.raise_for_status()

            response_data = resp.json()
            if 'data' not in response_data:
                raise VideoUrlExtractionError(f"Invalid response from Bilibili API: {response_data}")

            cid = response_data['data']['cid']
            query = sign({'bvid': bv_id, 'cid': cid, 'fnval': 144})
            video_url = f'https://api.bilibili.com/x/player/wbi/playurl?{query}'
            resp = requests.get(video_url, headers=headers)
            resp.raise_for_status()

            data = resp.json()['data']
            best_video_url = None
            best_audio_url = None

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
            )

        except requests.RequestException as e:
            raise VideoUrlExtractionError(f"Failed to fetch Bilibili video URL: {str(e)}")
        except KeyError as e:
            raise VideoUrlExtractionError(f"Missing expected data in Bilibili response: {str(e)}")
        except Exception as e:
            raise VideoUrlExtractionError(f"Unexpected error extracting Bilibili video URL: {str(e)}")
