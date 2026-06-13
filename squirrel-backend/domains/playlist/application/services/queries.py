from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

import domains.playlist.application.services.repository as repository
from infrastructure.database.session import get_session as _default_get_session
from domains.playlist.application.services.serialization import serialize_item, serialize_playlist

SessionFactory = Callable[[], Generator[Session, None, None]]


class PlaylistQueryService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def list_playlists(self, user_id: int) -> list[dict]:
        with self._session_factory() as session:
            playlists = repository.list_user_playlists(session, user_id=user_id)
            playlist_ids = [playlist.id for playlist in playlists]
            count_map = repository.load_playlist_item_counts(session, playlist_ids)
            return [serialize_playlist(playlist, count_map.get(playlist.id, 0)) for playlist in playlists]

    def get_playlist(self, user_id: int, playlist_id: int) -> dict | None:
        with self._session_factory() as session:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                return None
            return serialize_playlist(
                playlist,
                repository.count_playlist_items(session, playlist_id=playlist.id),
            )

    def get_playlist_items(self, user_id: int, playlist_id: int) -> list[dict] | None:
        with self._session_factory() as session:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                return None
            items = repository.list_playlist_items(session, playlist_id=playlist_id)
            return [serialize_item(item) for item in items]

    def get_playlist_detail(self, user_id: int, playlist_id: int) -> dict | None:
        with self._session_factory() as session:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                return None

            payload = serialize_playlist(
                playlist,
                repository.count_playlist_items(session, playlist_id=playlist.id),
            )
            payload['items'] = [
                serialize_item(item)
                for item in repository.list_playlist_items(session, playlist_id=playlist_id)
            ]
            return payload

    def get_playlist_items_with_videos(self, user_id: int, playlist_id: int) -> list[dict] | None:
        items = self.get_playlist_items(user_id, playlist_id)
        if items is None:
            return None

        video_map = self._load_item_video_map(items)
        enriched = []
        for item in items:
            video = video_map.get(item['video_id'])
            if video:
                item = item.copy()
                item['video'] = video.to_dict()
            enriched.append(item)

        return enriched

    def get_default_playlist(self, user_id: int) -> dict | None:
        with self._session_factory() as session:
            playlist = repository.get_default_playlist(session, user_id=user_id)
            if not playlist:
                return None

            return serialize_playlist(
                playlist,
                repository.count_playlist_items(session, playlist_id=playlist.id),
            )

    def _load_item_video_map(self, items: list[dict]) -> dict[int, object]:
        video_ids = [item['video_id'] for item in items]
        if not video_ids:
            return {}

        with self._session_factory() as session:
            return repository.load_videos_by_id(session, video_ids)
