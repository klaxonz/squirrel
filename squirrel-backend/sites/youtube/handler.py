import json
import subprocess
from abc import ABC
from typing import Tuple, Optional
from pytubefix import YouTube
from urllib.parse import quote
from core.exceptions.video_exceptions import VideoUrlExtractionError
from schemas.video.dto.video_dto import VideoUrlDto, QualityOptionDto
from sites.handler import VideoUrlHandler
from sites.handler_registry import register_handler
from models.video import Video


@register_handler
class YouTubeHandler(VideoUrlHandler, ABC):
    """Handler for YouTube video URLs"""

    domain = 'youtube.com'

    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            # Extract with pytube to build qualities list; prefer DASH via MPD
            yt = YouTube(video.url, 'WEB')

            qualities: list[QualityOptionDto] = []
            try:
                adaptive = yt.streams.filter(adaptive=True)
                seen = set()
                for s in adaptive:
                    height = getattr(s, 'height', None)
                    abr = getattr(s, 'abr', None)
                    # only collect video heights for UI; audio will be auto-selected in MPD
                    if height and height not in seen:
                        seen.add(height)
                        qualities.append(QualityOptionDto(
                            value=f"{height}p",
                            label=f"{height}p",
                            height=height,
                            bandwidth=None,
                            id=str(getattr(s, 'itag', ''))
                        ))
                # sort high -> low and add 'auto' on top
                qualities = sorted(qualities, key=lambda q: (q.height or 0), reverse=True)
                if not any(q.value == 'auto' for q in qualities):
                    qualities.insert(0, QualityOptionDto(value='auto', label='自动'))
            except Exception:
                qualities = [QualityOptionDto(value='auto', label='自动')]

            proxy_prefix_path = f"/api/video/proxy?domain=youtube.com"
            v_url = None
            a_url = None

            # Primary: return MPD endpoint so frontend uses DASH
            return VideoUrlDto(
                mpd_url=f"/api/video/mpd?video_id={video.id}",
                video_url=(f"{proxy_prefix_path}&url=" + quote(v_url)) if v_url else None,
                audio_url=(f"{proxy_prefix_path}&url=" + quote(a_url)) if a_url else None,
                qualities=qualities or None,
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
