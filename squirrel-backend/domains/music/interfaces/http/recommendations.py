from fastapi import APIRouter, Depends, Query

from domains.music.application.services.service import MusicService
from domains.user.application.services.auth import get_current_user
from domains.user.domain.models.user import User
from infrastructure.http import response

from .dependencies import get_music_service

router = APIRouter()


@router.get('/recommend')
async def get_music_recommendations(
    mode: str = Query('normal', description='发现模式: normal/small/peak'),
    song_pool_id: str | None = Query(None, description='AI 池: 0-Alpha 口味, 1-Beta 风格, 2-Gamma'),
    action: str | None = Query(None, description='操作: play/garbage'),
    hash: str | None = Query(None, description='当前音乐 hash'),
    songid: str | None = Query(None, description='当前音乐 songid'),
    playtime: int | None = Query(None, ge=0, description='已播放秒数'),
    is_overplay: bool = Query(False, description='是否播放完成'),
    remain_songcnt: int = Query(0, ge=0, description='剩余未播歌曲数'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_personal_fm_tracks(
            current_user.id,
            mode=mode,
            song_pool_id=song_pool_id,
            action=action,
            hash=hash,
            songid=songid,
            playtime=playtime,
            is_overplay=is_overplay,
            remain_songcnt=remain_songcnt,
        ),
    )


@router.get('/recommend/card')
async def get_music_recommend_card(
    card_id: int = Query(1, ge=1, le=6, description='推荐卡片 ID'),
    page_size: int = Query(10, ge=1, le=30, description='返回歌曲数量'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_recommend_card_tracks(current_user.id, card_id, page_size))


@router.get('/recommend/daily')
async def get_music_daily_recommend(
    page_size: int = Query(10, ge=1, le=30, description='返回歌曲数量'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_daily_recommend_tracks(current_user.id, page_size))


@router.get('/fm/garbage')
async def fm_garbage(
    hash: str = Query(..., min_length=1, description='音乐 hash'),
    songid: str | None = Query(None, description='音乐 songid'),
    playtime: int | None = Query(None, ge=0, description='已播放秒数'),
    mode: str = Query('normal', description='发现模式: normal/small/peak'),
    song_pool_id: str | None = Query(None, description='AI 池: 0-Alpha, 1-Beta, 2-Gamma'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_personal_fm_tracks(
            current_user.id,
            mode=mode,
            song_pool_id=song_pool_id,
            action='garbage',
            hash=hash,
            songid=songid,
            playtime=playtime,
            is_overplay=True,
        ),
    )


@router.get('/songs/new')
async def list_music_new_songs(
    type: int | None = Query(None, ge=1, description='新歌分类'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(30, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_new_songs(current_user.id, type, page, page_size))


@router.get('/albums/new')
async def list_music_new_albums(
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_new_albums(current_user.id, page, page_size))


@router.get('/recommend/ai')
async def get_music_ai_recommend(
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_ai_recommend_tracks(current_user.id, page_size))


@router.get('/recommend/brush')
async def get_music_brush_feed(
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_brush_feed(current_user.id, page_size))


@router.get('/recommend/everyday')
async def get_music_everyday_recommend(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_everyday_recommend(current_user.id))


@router.get('/recommend/style')
async def get_music_style_recommend(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_style_recommend(current_user.id))


@router.get('/banner')
async def get_music_banner(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_banner_list(current_user.id))
