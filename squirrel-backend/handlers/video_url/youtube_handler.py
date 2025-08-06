from pytubefix import YouTube
from dto.video_dto import VideoUrlDto
from handlers.video_url.base import VideoUrlHandler, VideoUrlExtractionError
from models.video import Video


class YouTubeHandler(VideoUrlHandler):
    """Handler for YouTube video URLs"""
    
    def supports_domain(self, domain: str) -> bool:
        return domain == 'youtube.com'
    
    def get_video_url(self, video: Video) -> VideoUrlDto:
        try:
            yt = YouTube(
                video.url,
                # use_po_token=True,
                # po_token_verifier=po_token_verifier
            )
            
            video_stream = yt.streams.filter(progressive=False, type="video").order_by('resolution').desc().first()
            audio_stream = yt.streams.filter(only_audio=True).order_by('abr').desc().first()
            
            return VideoUrlDto(
                video_url=video_stream.url if video_stream else None,
                audio_url=audio_stream.url if audio_stream else None,
            )
            
        except Exception as e:
            raise VideoUrlExtractionError(f"Failed to extract YouTube video URL: {str(e)}")
