from urllib.parse import quote
import phub
from dto.video_dto import VideoUrlDto
from handlers.video_url.base import VideoUrlHandler, VideoUrlExtractionError
from models.video import Video


class PornhubHandler(VideoUrlHandler):
    """Handler for Pornhub video URLs"""
    
    def supports_domain(self, domain: str) -> bool:
        return domain == 'pornhub.com'
    
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
