import logging
from fastapi import Query, APIRouter, Depends, Body
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from common import response
from core.database import get_session
from models.user import User
from models.playlist import Playlist
from models.playlist_item import PlaylistItem
from models.video import Video
from schemas.playlist import (
    PlaylistCreate,
    PlaylistUpdate,
    PlaylistItemAdd,
    PlaylistItemReorder,
)
from services import playlist_service
from utils.jwt_helper import get_current_user

logger = logging.getLogger()

router = APIRouter(prefix='/api/playlist', tags=['播放列表接口'])


@router.get("")
def list_playlists(
        current_user: User = Depends(get_current_user)
):
    playlists = playlist_service.list_playlists(current_user.id)
    return response.success(playlists)


@router.get("/{playlist_id}")
def get_playlist_detail(
        playlist_id: int,
        current_user: User = Depends(get_current_user)
):
    detail = playlist_service.get_playlist_detail(current_user.id, playlist_id)
    if not detail:
        return response.not_found("播放列表不存在")
    return response.success(detail)


@router.get("/{playlist_id}/items")
def get_playlist_items(
        playlist_id: int,
        current_user: User = Depends(get_current_user)
):
    items = playlist_service.get_playlist_items(current_user.id, playlist_id)
    if items is None:
        return response.not_found("播放列表不存在")

    with get_session() as session:
        video_ids = [item['video_id'] for item in items]
        if not video_ids:
            return response.success([])

        videos = session.scalars(
            select(Video).where(Video.id.in_(video_ids))
        ).all()
        video_map = {v.id: v for v in videos}

        enriched_items = []
        for item in items:
            video = video_map.get(item['video_id'])
            if video:
                item_data = item.copy()
                item_data['video'] = video.to_dict()
                enriched_items.append(item_data)
            else:
                enriched_items.append(item)

    return response.success(enriched_items)


@router.post("")
def create_playlist(
        data: PlaylistCreate,
        current_user: User = Depends(get_current_user)
):
    try:
        playlist = playlist_service.create_playlist(current_user.id, data)
        return response.success(playlist)
    except ValueError as e:
        return response.param_error(str(e))


@router.put("/{playlist_id}")
def update_playlist(
        playlist_id: int,
        data: PlaylistUpdate,
        current_user: User = Depends(get_current_user)
):
    try:
        playlist = playlist_service.update_playlist(current_user.id, playlist_id, data)
        if not playlist:
            return response.not_found("播放列表不存在")
        return response.success(playlist)
    except ValueError as e:
        return response.param_error(str(e))


@router.delete("/{playlist_id}")
def delete_playlist(
        playlist_id: int,
        current_user: User = Depends(get_current_user)
):
    try:
        ok = playlist_service.delete_playlist(current_user.id, playlist_id)
        if not ok:
            return response.not_found("播放列表不存在")
        return response.success({"deleted": True})
    except ValueError as e:
        return response.param_error(str(e))


@router.post("/items")
def add_video_to_playlist(
        data: PlaylistItemAdd,
        current_user: User = Depends(get_current_user)
):
    try:
        item = playlist_service.add_video_to_playlist(
            current_user.id,
            data.video_id,
            data.playlist_id,
        )
        return response.success(item)
    except ValueError as e:
        msg = str(e)
        if 'Video not found' in msg:
            return response.not_found(msg)
        if 'Playlist not found' in msg:
            return response.not_found(msg)
        return response.param_error(msg)


@router.delete("/{playlist_id}/items/{video_id}")
def remove_video_from_playlist(
        playlist_id: int,
        video_id: int,
        current_user: User = Depends(get_current_user)
):
    ok = playlist_service.remove_video_from_playlist(current_user.id, playlist_id, video_id)
    if not ok:
        return response.not_found("播放列表项不存在")
    return response.success({"removed": True})


@router.put("/items/reorder")
def reorder_playlist_item(
        data: PlaylistItemReorder,
        current_user: User = Depends(get_current_user)
):
    try:
        item = playlist_service.reorder_playlist_item(current_user.id, data)
        if not item:
            return response.not_found("播放列表项不存在")
        return response.success(item)
    except ValueError as e:
        return response.param_error(str(e))


@router.get("/default")
def get_default_playlist(
        current_user: User = Depends(get_current_user)
):
    playlist = playlist_service.get_default_playlist(current_user.id)
    if not playlist:
        return response.not_found("默认播放列表不存在")
    return response.success(playlist)


@router.post("/{playlist_id}/play-next")
def play_next_video(
        playlist_id: int,
        video_id: int = Query(..., description="当前播放的视频ID"),
        current_user: User = Depends(get_current_user)
):
    with get_session() as session:
        playlist = session.scalar(
            select(Playlist).where(
                Playlist.id == playlist_id,
                Playlist.user_id == current_user.id,
            )
        )
        if not playlist:
            return response.not_found("播放列表不存在")

        current_item = session.scalar(
            select(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.video_id == video_id,
            )
        )
        if not current_item:
            return response.not_found("视频不在播放列表中")

        next_item = session.scalar(
            select(PlaylistItem).where(
                PlaylistItem.playlist_id == playlist_id,
                PlaylistItem.position > current_item.position,
            ).order_by(PlaylistItem.position.asc())
        )

        if not next_item:
            next_item = session.scalar(
                select(PlaylistItem).where(
                    PlaylistItem.playlist_id == playlist_id,
                    PlaylistItem.position < current_item.position,
                ).order_by(PlaylistItem.position.asc())
            )

        if not next_item:
            return response.success({"has_next": False, "video_id": None})

        video = session.get(Video, next_item.video_id)
        if not video:
            return response.success({"has_next": False, "video_id": None})

        return response.success({
            "has_next": True,
            "video_id": next_item.video_id,
            "video": video.to_dict(),
        })
