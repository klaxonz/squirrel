from services.music._auth import MusicAuthMixin
from services.music._catalog import MusicCatalogMixin
from services.music._client import MusicClient, MusicServiceError
from services.music._comments import MusicCommentsMixin
from services.music._discovery import MusicDiscoveryMixin
from services.music._library import MusicLibraryMixin
from services.music._playback import MusicPlaybackMixin
from services.music._search import MusicSearchMixin
from services.music._video import MusicVideoMixin


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
