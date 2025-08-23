from abc import ABC
from urllib.parse import quote
import phub
from dto.video_dto import VideoUrlDto
from sites.handler import VideoUrlExtractionError, VideoUrlHandler
from sites.handler_registry import register_handler
from models.video import Video


@register_handler
class PornhubHandler(VideoUrlHandler, ABC):
    """Handler for Pornhub video URLs"""

    domain = 'pornhub.com'

    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            proxy_prefix_path = f"/api/video/proxy?domain=pornhub.com"

            client = phub.Client()
            video_obj = client.get(video.url)
            video_url = video_obj.get_m3u8_urls
            url = next(iter(video_url.values())) if video_url else None

            return VideoUrlDto(
                video_url=f"{proxy_prefix_path}&url=" + quote(url) if url else None,
                audio_url=None,
            )

        except Exception as e:
            raise VideoUrlExtractionError(f"Failed to extract Pornhub video URL: {str(e)}")
