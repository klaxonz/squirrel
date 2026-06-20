from collections.abc import Callable, Generator

from sqlalchemy.orm import Session

import domains.playlist.application.services.ordering as ordering
import domains.playlist.application.services.repository as repository
from domains.playlist.application.services.serialization import serialize_item, serialize_playlist
from domains.playlist.domain.models.playlist import Playlist
from domains.playlist.domain.models.playlist_item import PlaylistItem
from domains.playlist.interfaces.dto.playlist import PlaylistCreate, PlaylistItemReorder, PlaylistUpdate
from infrastructure.database.session import get_session as _default_get_session
from shared_kernel.domain.exceptions import ForbiddenError, NotFoundError

SessionFactory = Callable[[], Generator[Session, None, None]]


class PlaylistCommandService:
    def __init__(self, session_factory: SessionFactory | None = None):
        self._session_factory = session_factory or _default_get_session

    def create_playlist(self, user_id: int, data: PlaylistCreate) -> dict:
        with self._session_factory() as session:
            playlist = Playlist(
                user_id=user_id,
                name=data.name,
                description=data.description,
                is_default=False,
            )
            session.add(playlist)
            session.commit()
            session.refresh(playlist)
            return serialize_playlist(playlist, 0)

    def update_playlist(self, user_id: int, playlist_id: int, data: PlaylistUpdate) -> dict | None:
        with self._session_factory() as session:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                return None

            if playlist.is_default:
                raise ForbiddenError('Cannot modify default playlist')

            if data.name is not None:
                playlist.name = data.name
            if data.description is not None:
                playlist.description = data.description

            session.commit()
            session.refresh(playlist)

            return serialize_playlist(
                playlist,
                repository.count_playlist_items(session, playlist_id=playlist.id),
            )

    def delete_playlist(self, user_id: int, playlist_id: int) -> bool:
        with self._session_factory() as session:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                return False

            if playlist.is_default:
                raise ForbiddenError('Cannot delete default playlist')

            repository.delete_playlist_items(session, playlist_id=playlist_id)
            session.delete(playlist)
            session.commit()
            return True

    def add_video_to_playlist(self, user_id: int, video_id: int, playlist_id: int | None = None) -> dict:
        with self._session_factory() as session:
            video = repository.get_active_video(session, video_id=video_id)
            if not video:
                raise NotFoundError('Video')

            playlist = self._resolve_target_playlist(session, user_id=user_id, playlist_id=playlist_id)
            existing = repository.get_playlist_video_item(session, playlist_id=playlist.id, video_id=video_id)
            if existing:
                return serialize_item(existing)

            item = PlaylistItem(
                playlist_id=playlist.id,
                user_id=user_id,
                video_id=video_id,
                position=repository.max_item_position(session, playlist_id=playlist.id) + 1,
            )
            session.add(item)
            session.commit()
            session.refresh(item)
            return serialize_item(item)

    def remove_video_from_playlist(self, user_id: int, playlist_id: int, video_id: int) -> bool:
        with self._session_factory() as session:
            item = repository.get_playlist_item(session, playlist_id=playlist_id, user_id=user_id, video_id=video_id)
            if not item:
                return False

            deleted_position = item.position
            session.delete(item)
            session.flush()
            ordering.compact_positions_after_delete(
                session,
                playlist_id=playlist_id,
                deleted_position=deleted_position,
            )

            session.commit()
            return True

    def reorder_playlist_item(self, user_id: int, data: PlaylistItemReorder) -> dict | None:
        with self._session_factory() as session:
            item = repository.get_playlist_item(
                session,
                playlist_id=data.playlist_id,
                user_id=user_id,
                video_id=data.video_id,
            )
            if not item:
                return None

            ordering.move_item(
                session,
                item=item,
                new_position=data.new_position,
                max_position=repository.max_item_position(session, playlist_id=data.playlist_id),
            )
            session.commit()
            session.refresh(item)
            return serialize_item(item)

    @staticmethod
    def _resolve_target_playlist(session: Session, *, user_id: int, playlist_id: int | None) -> Playlist:
        if playlist_id:
            playlist = repository.get_user_playlist(session, user_id=user_id, playlist_id=playlist_id)
            if not playlist:
                raise NotFoundError('Playlist')
            return playlist

        return repository.get_or_create_default_playlist(session, user_id=user_id)
