from services.playlist.commands import PlaylistCommandService
from services.playlist.playback import PlaylistPlaybackService
from services.playlist.queries import PlaylistQueryService


def get_playlist_query_service() -> PlaylistQueryService:
    return PlaylistQueryService()


def get_playlist_command_service() -> PlaylistCommandService:
    return PlaylistCommandService()


def get_playlist_playback_service() -> PlaylistPlaybackService:
    return PlaylistPlaybackService()
