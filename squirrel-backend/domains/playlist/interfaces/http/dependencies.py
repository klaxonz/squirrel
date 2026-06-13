from domains.playlist.application.services.commands import PlaylistCommandService
from domains.playlist.application.services.playback import PlaylistPlaybackService
from domains.playlist.application.services.queries import PlaylistQueryService


def get_playlist_query_service() -> PlaylistQueryService:
    return PlaylistQueryService()


def get_playlist_command_service() -> PlaylistCommandService:
    return PlaylistCommandService()


def get_playlist_playback_service() -> PlaylistPlaybackService:
    return PlaylistPlaybackService()
