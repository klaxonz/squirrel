from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from schemas.music import MusicPlaylistCollect, MusicPlaylistCreate, MusicPlaylistTrackAdd, MusicPlayHistoryReport
from services import music_service
from utils.jwt_helper import get_current_user

router = APIRouter(tags=['音乐接口'])


@router.get('/api/music/search')
def search_music(
    query: str = Query(..., min_length=1, max_length=100, description='搜索关键词'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error('query cannot be empty')

    try:
        return response.success(music_service.search_tracks(current_user.id, normalized_query, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/auth/status')
def get_music_auth_status(
    current_user: User = Depends(get_current_user),
):
    return response.success(music_service.get_auth_status(current_user.id))


@router.get('/api/music/ranks')
def list_music_ranks(
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.list_ranks(current_user.id))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/rank/tracks')
def get_music_rank_tracks(
    rank_id: str = Query(..., min_length=1, description='排行榜 ID'),
    rank_cid: str | None = Query(None, description='排行榜期次 ID'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_rank_tracks(current_user.id, rank_id, rank_cid, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/playlists')
def list_music_playlists(
    category_id: int = Query(0, ge=0, description='歌单分类 ID'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.list_playlists(current_user.id, category_id, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/playlist/tracks')
def get_music_playlist_tracks(
    playlist_id: str = Query(..., min_length=1, description='歌单 ID'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(20, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_playlist_tracks(current_user.id, playlist_id, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/user/playlists')
def list_music_user_playlists(
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(30, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.list_user_playlists(current_user.id, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/user/playlist/tracks')
def get_music_user_playlist_tracks(
    list_id: str = Query(..., min_length=1, description='用户歌单 listid'),
    page: int = Query(1, ge=1, le=50, description='页码'),
    page_size: int = Query(30, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_user_playlist_tracks(current_user.id, list_id, page, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.post('/api/music/user/playlists')
def create_music_user_playlist(
    data: MusicPlaylistCreate,
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.create_user_playlist(current_user.id, data.name, data.is_private))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.post('/api/music/user/playlists/collect')
def collect_music_playlist(
    data: MusicPlaylistCollect,
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.collect_playlist(current_user.id, data.playlist_id))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.delete('/api/music/user/playlists')
def delete_music_user_playlist(
    list_id: str = Query(..., min_length=1, description='用户歌单 listid'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.delete_user_playlist(current_user.id, list_id))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.post('/api/music/user/playlist/tracks')
def add_music_user_playlist_track(
    data: MusicPlaylistTrackAdd,
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.add_track_to_user_playlist(current_user.id, data.list_id, data.track))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.delete('/api/music/user/playlist/tracks')
def remove_music_user_playlist_tracks(
    list_id: str = Query(..., min_length=1, description='用户歌单 listid'),
    file_ids: str = Query(..., min_length=1, description='歌曲 fileid，多个用逗号分隔'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.remove_tracks_from_user_playlist(current_user.id, list_id, file_ids))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/user/history')
def get_music_user_history(
    bp: str | None = Query(None, description='上一页返回的 bp'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_user_history(current_user.id, bp))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/user/listen-rank')
def get_music_user_listen_rank(
    history_type: int = Query(0, alias='type', ge=0, le=1, description='0 最近一周，1 全部累计'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_user_listen_rank(current_user.id, history_type))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/latest-songs/listen')
def get_music_latest_listen_songs(
    page_size: int = Query(30, ge=1, le=50, description='每页数量'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_latest_listen_songs(current_user.id, page_size))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.post('/api/music/auth/qr')
def create_music_qr_login(
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.create_qr_login())
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/auth/qr/check')
def check_music_qr_login(
    key: str = Query(..., min_length=1, description='二维码 key'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.check_qr_login(current_user.id, key))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.post('/api/music/playhistory')
def upload_music_play_history(
    data: MusicPlayHistoryReport,
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(
            music_service.upload_play_history(current_user.id, data.album_audio_id, data.played_at, data.play_count)
        )
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/favorite/count')
def get_music_favorite_count(
    mixsongids: str = Query(..., min_length=1, description='音乐 mixsongid，多个用逗号分隔'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_favorite_counts(current_user.id, mixsongids))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/play-url')
def get_music_play_url(
    hash: str = Query(..., min_length=1, description='音乐 hash'),
    album_audio_id: str | None = Query(None, description='专辑音频 ID'),
    quality: str = Query('128', description='音质'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(music_service.get_track_play_url(current_user.id, hash, album_audio_id, quality))
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))


@router.get('/api/music/lyric')
def get_music_lyric(
    title: str = Query(..., min_length=1, description='歌曲名'),
    artist: str = Query('', description='歌手名'),
    hash: str = Query(..., min_length=1, description='音乐 hash'),
    album_audio_id: str | None = Query(None, description='专辑音频 ID'),
    duration: int = Query(0, ge=0, description='歌曲时长'),
    current_user: User = Depends(get_current_user),
):
    try:
        return response.success(
            music_service.get_track_lyric(current_user.id, title, artist, hash, album_audio_id, duration)
        )
    except music_service.MusicServiceError as exc:
        return response.server_error(str(exc))
