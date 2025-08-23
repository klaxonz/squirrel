from urllib.parse import urlparse
from typing import Tuple
from models.video import Video
from sites.subtitles_registry import SubtitlesRegistry


class SubtitlesFactory:
    @staticmethod
    def get_subtitles_for_video(video: Video, lang: str, fmt: str = "srt") -> Tuple[str, str]:
        if not video or not getattr(video, 'url', None):
            raise ValueError("Invalid video: missing URL")
        parsed = urlparse(video.url)
        parts = parsed.netloc.split('.')
        for i in range(len(parts) - 1):
            domain = '.'.join(parts[i:])
            provider_cls = SubtitlesRegistry.get_provider_class(domain)
            if provider_cls:
                provider = provider_cls()
                return provider.get_subtitles(video, lang, fmt)
        supported = SubtitlesRegistry.get_supported_domains()
        raise ValueError(
            f"No subtitles provider registered for domain '{parsed.netloc}'. Supported domains: {supported}"
        )

