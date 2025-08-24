import json
import subprocess
from abc import ABC
from typing import Tuple, Optional
from pytubefix import YouTube
from urllib.parse import quote
from core.exceptions.video_exceptions import VideoUrlExtractionError
from schemas.video.dto.video_dto import VideoUrlDto
from sites.handler import VideoUrlHandler
from sites.handler_registry import register_handler
from models.video import Video


@register_handler
class YouTubeHandler(VideoUrlHandler, ABC):
    """Handler for YouTube video URLs"""

    domain = 'youtube.com'

    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            # Keep extraction to verify availability, but we will prefer DASH (MPD) like Bilibili
            yt = YouTube(
                video.url, 'WEB'
                # use_po_token=True,
                # po_token_verifier=po_token_verifier
            )

            # video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
            # audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()

            proxy_prefix_path = f"/api/video/proxy?domain=youtube.com"
            v_url = None
            a_url = None

            # Primary: return MPD endpoint so frontend uses DASH like bilibili
            return VideoUrlDto(
                mpd_url=f"/api/video/mpd?video_id={video.id}",
                video_url=(f"{proxy_prefix_path}&url=" + quote(v_url)) if v_url else None,
                audio_url=(f"{proxy_prefix_path}&url=" + quote(a_url)) if a_url else None,
            )

        except Exception as e:
            raise VideoUrlExtractionError(f"Failed to extract YouTube video URL: {str(e)}")


def po_token_verifier(_: None = None) -> Optional[Tuple[str, str]]:
    token_object = generate_youtube_token()
    return token_object["visitorData"], token_object["poToken"]


def generate_youtube_token() -> dict:
    try:
        result = subprocess.run(
            ["node", "scripts/youtube-token-generator.js"],
            capture_output=True,
            text=True,
            check=True
        )
        return json.loads(result.stdout)
    except (subprocess.CalledProcessError, json.JSONDecodeError) as e:
        raise Exception(f"Failed to generate YouTube token: ", e)
