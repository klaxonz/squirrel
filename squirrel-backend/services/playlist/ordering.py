from __future__ import annotations

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.playlist_item import PlaylistItem


def compact_positions_after_delete(session: Session, *, playlist_id: int, deleted_position: int) -> None:
    session.execute(
        update(PlaylistItem)
        .where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.position > deleted_position,
        )
        .values(position=PlaylistItem.position - 1),
    )


def move_item(session: Session, *, item: PlaylistItem, new_position: int, max_position: int) -> None:
    old_position = item.position
    bounded_position = max(1, min(new_position, max_position))

    if old_position == bounded_position:
        return

    if old_position < bounded_position:
        session.execute(
            update(PlaylistItem)
            .where(
                PlaylistItem.playlist_id == item.playlist_id,
                PlaylistItem.position > old_position,
                PlaylistItem.position <= bounded_position,
            )
            .values(position=PlaylistItem.position - 1),
        )
    else:
        session.execute(
            update(PlaylistItem)
            .where(
                PlaylistItem.playlist_id == item.playlist_id,
                PlaylistItem.position >= bounded_position,
                PlaylistItem.position < old_position,
            )
            .values(position=PlaylistItem.position + 1),
        )

    item.position = bounded_position


def find_next_item(session: Session, *, playlist_id: int, current_position: int) -> PlaylistItem | None:
    next_item = session.scalar(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.position > current_position,
        ).order_by(PlaylistItem.position.asc()),
    )
    if next_item:
        return next_item

    return session.scalar(
        select(PlaylistItem).where(
            PlaylistItem.playlist_id == playlist_id,
            PlaylistItem.position < current_position,
        ).order_by(PlaylistItem.position.asc()),
    )
