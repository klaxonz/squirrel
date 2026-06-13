from __future__ import annotations

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from domains.playlist.domain.models.playlist import Playlist
from domains.playlist.domain.models.playlist_item import PlaylistItem
from domains.video.domain.models.video import Video


def get_user_playlist(session: Session, *, user_id: int, playlist_id: int) -> Playlist | None:
    return session.scalar(
        select(Playlist).where(
            Playlist.id == playlist_id,
            Playlist.user_id == user_id,
        ),
    )


def get_default_playlist(session: Session, *, user_id: int) -> Playlist | None:
    return session.scalar(
        select(Playlist).where(
            Playlist.user_id == user_id,
            Playlist.is_default,
        ),
    )


def get_or_create_default_playlist(session: Session, *, user_id: int) -> Playlist:
    default = get_default_playlist(session, user_id=user_id)
    if default:
        return default

    default = Playlist(
        user_id=user_id,
        name='稍后再看',
        description='稍后再看的视频列表',
        is_default=True,
    )
    session.add(default)
    session.flush()
    return default


def list_user_playlists(session: Session, *, user_id: int) -> list[Playlist]:
    return list(
        session.scalars(
            select(Playlist)
            .where(Playlist.user_id == user_id)
            .order_by(Playlist.is_default.desc(), Playlist.created_at.desc()),
        ).all(),
    )


def load_playlist_item_counts(session: Session, playlist_ids: list[int]) -> dict[int, int]:
    if not playlist_ids:
        return {}

    count_rows = session.execute(
        select(PlaylistItem.playlist_id, func.count(PlaylistItem.id))
        .where(PlaylistItem.playlist_id.in_(playlist_ids))
        .group_by(PlaylistItem.playlist_id),
    ).all()
    return {int(playlist_id): int(count or 0) for playlist_id, count in count_rows}


def count_playlist_items(session: Session, *, playlist_id: int) -> int:
    return int(
        session.scalar(
            select(func.count(PlaylistItem.id))
            .where(PlaylistItem.playlist_id == playlist_id),
        )
        or 0,
    )


def list_playlist_items(session: Session, *, playlist_id: int) -> list[PlaylistItem]:
    return list(
        session.scalars(
            select(PlaylistItem)
            .where(PlaylistItem.playlist_id == playlist_id)
            .order_by(PlaylistItem.position.asc(), PlaylistItem.added_at.asc()),
        ).all(),
    )


def get_playlist_item(session: Session, *, playlist_id: int, user_id: int, video_id: int) -> PlaylistItem | None:
    return session.scalar(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.user_id == user_id,
            PlaylistItem.video_id == video_id,
        ),
    )


def get_playlist_video_item(session: Session, *, playlist_id: int, video_id: int) -> PlaylistItem | None:
    return session.scalar(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.video_id == video_id,
        ),
    )


def max_item_position(session: Session, *, playlist_id: int) -> int:
    return int(
        session.scalar(
            select(func.max(PlaylistItem.position))
            .where(PlaylistItem.playlist_id == playlist_id),
        )
        or 0,
    )


def get_active_video(session: Session, *, video_id: int) -> Video | None:
    video = session.get(Video, video_id)
    if not video or video.is_deleted:
        return None
    return video


def get_video(session: Session, *, video_id: int) -> Video | None:
    return session.get(Video, video_id)


def load_videos_by_id(session: Session, video_ids: list[int]) -> dict[int, Video]:
    if not video_ids:
        return {}

    videos = session.scalars(
        select(Video).where(Video.id.in_(video_ids)),
    ).all()
    return {int(video.id): video for video in videos}


def delete_playlist_items(session: Session, *, playlist_id: int) -> None:
    session.execute(
        delete(PlaylistItem).where(PlaylistItem.playlist_id == playlist_id),
    )
