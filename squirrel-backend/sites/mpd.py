from urllib.parse import urlparse
from models.video import Video
from sites.mpd_registry import MpdRegistry


class MpdFactory:
    @staticmethod
    def build_mpd_for_video(video: Video) -> str:
        """
        Resolve the site-specific MPD builder based on the video's URL domain
        and return the MPD XML string.
        """
        if not video or not getattr(video, 'url', None):
            raise ValueError("Invalid video: missing URL")

        parsed = urlparse(video.url)
        domain_parts = parsed.netloc.split('.')

        # Try subdomain to parent domain matching
        for i in range(len(domain_parts) - 1):
            current_domain = '.'.join(domain_parts[i:])
            builder_cls = MpdRegistry.get_mpd_builder_class(current_domain)
            if builder_cls:
                builder = builder_cls()
                return builder.build_mpd(video)

        supported = MpdRegistry.get_supported_domains()
        raise ValueError(
            f"No MPD builder registered for domain '{parsed.netloc}'. Supported domains: {supported}"
        )

