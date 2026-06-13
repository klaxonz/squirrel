from domains.music.application.services._auth import MusicAuthMixin
from domains.music.application.services._catalog import MusicCatalogMixin
from domains.music.application.services._client import MusicClient, MusicServiceError
from domains.music.application.services._comments import MusicCommentsMixin
from domains.music.application.services._discovery import MusicDiscoveryMixin
from domains.music.application.services._library import MusicLibraryMixin
from domains.music.application.services._playback import MusicPlaybackMixin
from domains.music.application.services._search import MusicSearchMixin
from domains.music.application.services._video import MusicVideoMixin


class MusicService(
    MusicSearchMixin,
    MusicCatalogMixin,
    MusicCommentsMixin,
    MusicDiscoveryMixin,
    MusicLibraryMixin,
    MusicPlaybackMixin,
    MusicVideoMixin,
    MusicAuthMixin,
):
    Error = MusicServiceError

    def __init__(self, redis_client=None, http_client=None, settings=None):
        self._client = MusicClient(
            redis_client=redis_client,
            http_client=http_client,
            settings=settings,
        )

    async def aclose(self) -> None:
        await self._client.aclose()
