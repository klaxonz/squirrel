from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

import domains.playlist.application.services.ordering as ordering
import domains.playlist.application.services.repository as repository
from infrastructure.database.session import get_session as _default_get_session

SessionFactory = Callable[[], Generator[Session, None, None]]


class PlaylistPlaybackService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def play_next_video(self, user_id: int, playlist_id: int, video_id: int) -> dict | None:
        with self._session_factory() as session:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                return None

            current_item = repository.get_playlist_video_item(session, playlist_id=playlist_id, video_id=video_id)
            if not current_item:
                return {'error': '视频不在播放列表中'}

            next_item = ordering.find_next_item(
                session,
                playlist_id=playlist_id,
                current_position=current_item.position,
            )
            if not next_item:
                return {'has_next': False, 'video_id': None}

            video = repository.get_video(session, video_id=next_item.video_id)
            if not video:
                return {'has_next': False, 'video_id': None}

            return {
                'has_next': True,
                'video_id': next_item.video_id,
                'video': video.to_dict(),
            }
