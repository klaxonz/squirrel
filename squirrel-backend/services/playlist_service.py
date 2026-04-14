from sqlalchemy import delete, select, func, update

from core.database import get_session
from models.playlist import Playlist
from models.playlist_item import PlaylistItem
from models.video import Video
from schemas.playlist import PlaylistCreate, PlaylistUpdate, PlaylistItemReorder


def _serialize_playlist(playlist: Playlist, video_count: int = 0) -> dict:
    payload = playlist.to_dict()
    payload['video_count'] = video_count
    return payload


def _serialize_item(item: PlaylistItem) -> dict:
    payload = item.to_dict()
    return payload


def _get_or_create_default_playlist(session, user_id: int) -> Playlist:
    default = session.scalar(
        select(Playlist).where(
            Playlist.user_id == user_id,
            Playlist.is_default == True,
        )
    )
    if not default:
        default = Playlist(
            user_id=user_id,
            name='稍后再看',
            description='稍后再看的视频列表',
            is_default=True,
        )
        session.add(default)
        session.flush()
    return default


def list_playlists(user_id: int) -> list[dict]:
    with get_session() as session:
        playlists = session.scalars(
            select(Playlist)
            .where(Playlist.user_id == user_id)
            .order_by(Playlist.is_default.desc(), Playlist.created_at.desc())
        ).all()

        result = []
        for p in playlists:
            count = session.scalar(
                select(func.count(PlaylistItem.id))
                .where(PlaylistItem.playlist_id == p.id)
            ) or 0
            result.append(_serialize_playlist(p, count))
        return result


def get_playlist(user_id: int, playlist_id: int) -> dict | None:
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
            )
        )
        if not playlist:
            return None

        count = session.scalar(
            select(func.count(PlaylistItem.id))
            .where(PlaylistItem.playlist_id == playlist.id)
        ) or 0

        return _serialize_playlist(playlist, count)


def get_playlist_items(user_id: int, playlist_id: int) -> list[dict] | None:
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
            )
        )
        if not playlist:
            return None

        items = session.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc(), PlaylistItem.added_at.asc())
        ).all()

        return [_serialize_item(item) for item in items]


def get_playlist_detail(user_id: int, playlist_id: int) -> dict | None:
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
            )
        )
        if not playlist:
            return None

        count = session.scalar(
            select(func.count(PlaylistItem.id))
            .where(PlaylistItem.playlist_id == playlist.id)
        ) or 0

        items = session.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc(), PlaylistItem.added_at.asc())
        ).all()

        payload = _serialize_playlist(playlist, count)
        payload['items'] = [_serialize_item(item) for item in items]
        return payload


def create_playlist(user_id: int, data: PlaylistCreate) -> dict:
    with get_session() as session:
        playlist = Playlist(
            user_id=user_id,
            name=data.name,
            description=data.description,
            is_default=False,
        )
        session.add(playlist)
        session.commit()
        session.refresh(playlist)
        return _serialize_playlist(playlist, 0)


def update_playlist(user_id: int, playlist_id: int, data: PlaylistUpdate) -> dict | None:
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
            )
        )
        if not playlist:
            return None

        if playlist.is_default:
            raise ValueError('Cannot modify default playlist')

        if data.name is not None:
            playlist.name = data.name
        if data.description is not None:
            playlist.description = data.description

        session.commit()
        session.refresh(playlist)

        count = session.scalar(
            select(func.count(PlaylistItem.id))
            .where(PlaylistItem.playlist_id == playlist.id)
        ) or 0

        return _serialize_playlist(playlist, count)


def delete_playlist(user_id: int, playlist_id: int) -> bool:
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == user_id,
            )
        )
        if not playlist:
            return False

        if playlist.is_default:
            raise ValueError('Cannot delete default playlist')

        session.execute(
            delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id)
        )
        session.delete(playlist)
        session.commit()
        return True


def add_video_to_playlist(user_id: int, video_id: int, playlist_id: int | None = None) -> dict:
    with get_session() as session:
        video = session.get(Video, video_id)
        if not video or getattr(video, 'is_deleted', False):
            raise ValueError('Video not found')

        if playlist_id:
            playlist = session.scalar(
                select(Playlist).where(
                    Playlist.id == playlist_id,
                    Playlist.user_id == user_id,
                )
            )
            if not playlist:
                raise ValueError('Playlist not found')
        else:
            playlist = _get_or_create_default_playlist(session, user_id)

        existing = session.scalar(
            select(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist.id,
                PlaylistItem.video_id == video_id,
            )
        )
        if existing:
            return _serialize_item(existing)

        max_position = session.scalar(
            select(func.max(PlaylistItem.position))
            .where(PlaylistItem.playlist_id == playlist.id)
        ) or 0

        item = PlaylistItem(
            playlist_id=playlist.id,
            user_id=user_id,
            video_id=video_id,
            position=max_position + 1,
        )
        session.add(item)
        session.commit()
        session.refresh(item)
        return _serialize_item(item)


def remove_video_from_playlist(user_id: int, playlist_id: int, video_id: int) -> bool:
    with get_session() as session:
        item = session.scalar(
            select(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.user_id == user_id,
                PlaylistItem.video_id == video_id,
            )
        )
        if not item:
            return False

        deleted_position = item.position
        session.delete(item)
        session.flush()

        session.execute(
            update(PlaylistItem)
            .where(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.position > deleted_position,
            )
            .values(position=PlaylistItem.position - 1)
        )

        session.commit()
        return True


def reorder_playlist_item(user_id: int, data: PlaylistItemReorder) -> dict | None:
    with get_session() as session:
        item = session.scalar(
            select(PlaylistItem).where(
                PlaylistItem.playlist_id == data.playlist_id,
                PlaylistItem.user_id == user_id,
                PlaylistItem.video_id == data.video_id,
            )
        )
        if not item:
            return None

        old_position = item.position
        new_position = data.new_position

        max_pos_result = session.scalar(
            select(func.max(PlaylistItem.position))
            .where(PlaylistItem.playlist_id == data.playlist_id)
        )
        max_position = max_pos_result if max_pos_result is not None else 0
        new_position = max(1, min(new_position, max_position))

        if old_position == new_position:
            return _serialize_item(item)

        if old_position < new_position:
            session.execute(
                update(PlaylistItem)
                .where(
                    PlaylistItem.playlist_id == data.playlist_id,
                    PlaylistItem.position > old_position,
                    PlaylistItem.position <= new_position,
                )
                .values(position=PlaylistItem.position - 1)
            )
        else:
            session.execute(
                update(PlaylistItem)
                .where(
                    PlaylistItem.playlist_id == data.playlist_id,
                    PlaylistItem.position >= new_position,
                    PlaylistItem.position < old_position,
                )
                .values(position=PlaylistItem.position + 1)
            )

        item.position = new_position
        session.commit()
        session.refresh(item)
        return _serialize_item(item)


def get_default_playlist(user_id: int) -> dict | None:
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.user_id == user_id,
                Playlist.is_default == True,
            )
        )
        if not playlist:
            return None

        count = session.scalar(
            select(func.count(PlaylistItem.id))
            .where(PlaylistItem.playlist_id == playlist.id)
        ) or 0

        return _serialize_playlist(playlist, count)
