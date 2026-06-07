from functools import wraps

from fastapi import APIRouter, Depends, Query

from common import response
from models.user import User
from schemas.music import MusicPlayHistoryReport, MusicPlaylistCollect, MusicPlaylistCreate, MusicPlaylistTrackAdd
from services.music import MusicService, MusicServiceError
from utils.jwt_helper import get_current_user

router = APIRouter(prefix="/api/music", tags=["音乐接口"])


async def get_music_service():
    return MusicService()


def _handle_music_error(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except MusicServiceError as exc:
            return response.server_error(str(exc))
    return wrapper


@router.get("/search")
async def search_music(
    query: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error("query cannot be empty")

    return response.success(await music_service.search_tracks(current_user.id, normalized_query, page, page_size))


@router.get("/search/artists")
async def search_music_artists(
    query: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(10, ge=1, le=30, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error("query cannot be empty")

    return response.success(await music_service.search_artists(current_user.id, normalized_query, page, page_size))


@router.get("/search/albums")
async def search_music_albums(
    query: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(12, ge=1, le=30, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error("query cannot be empty")

    return response.success(await music_service.search_albums(current_user.id, normalized_query, page, page_size))


@router.get("/search/default")
async def get_music_default_search(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_default_search_keyword(current_user.id))


@router.get("/search/hot")
async def list_music_hot_searches(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_hot_searches(current_user.id))


@router.get("/search/suggest")
async def suggest_music_search(
    query: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error("query cannot be empty")

    return response.success(await music_service.search_suggestions(current_user.id, normalized_query))


@router.get("/auth/status")
async def get_music_auth_status(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_auth_status(current_user.id))


@router.get("/recommend")
async def get_music_recommendations(
    mode: str = Query("normal", description="发现模式: normal/small/peak"),
    song_pool_id: str | None = Query(None, description="AI 池: 0-Alpha 口味, 1-Beta 风格, 2-Gamma"),
    action: str | None = Query(None, description="操作: play/garbage"),
    hash: str | None = Query(None, description="当前音乐 hash"),
    songid: str | None = Query(None, description="当前音乐 songid"),
    playtime: int | None = Query(None, ge=0, description="已播放秒数"),
    is_overplay: bool = Query(False, description="是否播放完成"),
    remain_songcnt: int = Query(0, ge=0, description="剩余未播歌曲数"),
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


@router.get("/recommend/card")
async def get_music_recommend_card(
    card_id: int = Query(1, ge=1, le=6, description="推荐卡片 ID"),
    page_size: int = Query(10, ge=1, le=30, description="返回歌曲数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_recommend_card_tracks(current_user.id, card_id, page_size))


@router.get("/recommend/daily")
async def get_music_daily_recommend(
    page_size: int = Query(10, ge=1, le=30, description="返回歌曲数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_daily_recommend_tracks(current_user.id, page_size))


@router.get("/fm/garbage")
async def fm_garbage(
    hash: str = Query(..., min_length=1, description="音乐 hash"),
    songid: str | None = Query(None, description="音乐 songid"),
    playtime: int | None = Query(None, ge=0, description="已播放秒数"),
    mode: str = Query("normal", description="发现模式: normal/small/peak"),
    song_pool_id: str | None = Query(None, description="AI 池: 0-Alpha, 1-Beta, 2-Gamma"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_personal_fm_tracks(
            current_user.id,
            mode=mode,
            song_pool_id=song_pool_id,
            action="garbage",
            hash=hash,
            songid=songid,
            playtime=playtime,
            is_overplay=True,
        ),
    )


@router.get("/ranks")
async def list_music_ranks(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_ranks(current_user.id))


@router.get("/rank/tracks")
async def get_music_rank_tracks(
    rank_id: str = Query(..., min_length=1, description="排行榜 ID"),
    rank_cid: str | None = Query(None, description="排行榜期次 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_rank_tracks(current_user.id, rank_id, rank_cid, page, page_size))


@router.get("/playlists")
async def list_music_playlists(
    category_id: int = Query(0, ge=0, description="歌单分类 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_playlists(current_user.id, category_id, page, page_size))


@router.get("/playlist/tags")
async def list_music_playlist_tags(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_playlist_tags(current_user.id))


@router.get("/playlist/similar")
async def get_music_similar_playlists(
    playlist_id: str = Query(..., min_length=1, description="歌单 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_similar_playlists(current_user.id, playlist_id))


@router.get("/playlist/tracks")
async def get_music_playlist_tracks(
    playlist_id: str = Query(..., min_length=1, description="歌单 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_playlist_tracks(current_user.id, playlist_id, page, page_size))


@router.get("/user/playlists")
async def list_music_user_playlists(
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_user_playlists(current_user.id, page, page_size))


@router.get("/user/playlist/tracks")
async def get_music_user_playlist_tracks(
    list_id: str = Query(..., min_length=1, description="用户歌单 listid"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_playlist_tracks(current_user.id, list_id, page, page_size))


@router.get("/artist/detail")
async def get_music_artist_detail(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_detail(current_user.id, artist_id))


@router.get("/artist/tracks")
async def get_music_artist_tracks(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_tracks(current_user.id, artist_id, page, page_size))


@router.get("/artist/albums")
async def get_music_artist_albums(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_albums(current_user.id, artist_id, page, page_size))


@router.get("/album/detail")
async def get_music_album_detail(
    album_id: str = Query(..., min_length=1, description="专辑 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_album_detail(current_user.id, album_id))


@router.get("/album/tracks")
async def get_music_album_tracks(
    album_id: str = Query(..., min_length=1, description="专辑 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_album_tracks(current_user.id, album_id, page, page_size))


@router.get("/songs/new")
async def list_music_new_songs(
    type: int | None = Query(None, ge=1, description="新歌分类"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_new_songs(current_user.id, type, page, page_size))


@router.post("/user/playlists")
async def create_music_user_playlist(
    data: MusicPlaylistCreate,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.create_user_playlist(current_user.id, data.name, data.is_private))


@router.post("/user/playlists/collect")
async def collect_music_playlist(
    data: MusicPlaylistCollect,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.collect_playlist(current_user.id, data.playlist_id))


@router.delete("/user/playlists")
async def delete_music_user_playlist(
    list_id: str = Query(..., min_length=1, description="用户歌单 listid"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.delete_user_playlist(current_user.id, list_id))


@router.post("/user/playlist/tracks")
async def add_music_user_playlist_track(
    data: MusicPlaylistTrackAdd,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.add_track_to_user_playlist(current_user.id, data.list_id, data.track))


@router.delete("/user/playlist/tracks")
async def remove_music_user_playlist_tracks(
    list_id: str = Query(..., min_length=1, description="用户歌单 listid"),
    file_ids: str = Query(..., min_length=1, description="歌曲 fileid，多个用逗号分隔"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.remove_tracks_from_user_playlist(current_user.id, list_id, file_ids))


@router.get("/user/history")
async def get_music_user_history(
    bp: str | None = Query(None, description="上一页返回的 bp"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_history(current_user.id, bp))


@router.get("/user/listen-rank")
async def get_music_user_listen_rank(
    history_type: int = Query(0, alias="type", ge=0, le=1, description="0 最近一周，1 全部累计"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_listen_rank(current_user.id, history_type))


@router.get("/latest-songs/listen")
async def get_music_latest_listen_songs(
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_latest_listen_songs(current_user.id, page_size))


@router.post("/auth/qr")
async def create_music_qr_login(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.create_qr_login())


@router.get("/user/profile")
async def get_music_user_profile(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_profile(current_user.id))


@router.post("/user/logout")
async def logout_music_user(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.logout(current_user.id))


@router.get("/auth/qr/check")
async def check_music_qr_login(
    key: str = Query(..., min_length=1, description="二维码 key"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.check_qr_login(current_user.id, key))


@router.post("/auth/logout")
async def logout_music(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    await music_service.clear_auth(current_user.id)
    return response.success({"ok": True})


@router.post("/playhistory")
async def upload_music_play_history(
    data: MusicPlayHistoryReport,
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.upload_play_history(current_user.id, data.album_audio_id, data.played_at, data.play_count),
    )


@router.get("/favorite/count")
async def get_music_favorite_count(
    mixsongids: str = Query(..., min_length=1, description="音乐 mixsongid，多个用逗号分隔"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_favorite_counts(current_user.id, mixsongids))


@router.get("/play-url")
async def get_music_play_url(
    hash: str = Query(..., min_length=1, description="音乐 hash"),
    album_audio_id: str | None = Query(None, description="专辑音频 ID"),
    quality: str = Query("128", description="音质"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_track_play_url(current_user.id, hash, album_audio_id, quality))


@router.get("/song/climax")
async def get_music_track_climax(
    hash: str = Query(..., min_length=1, description="音乐 hash，多个用逗号分隔"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_track_climax(current_user.id, hash))


@router.get("/song/related")
async def get_music_related_tracks(
    album_audio_id: str = Query(..., min_length=1, description="专辑音频 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    sort: str = Query("all", pattern="^(all|hot|new)$", description="排序"),
    type: str | None = Query(None, description="分类"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_related_tracks(current_user.id, album_audio_id, page, page_size, sort, type),
    )


@router.get("/song/mv")
async def get_music_track_mv(
    album_audio_id: str = Query(..., min_length=1, description="专辑音频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_track_mv(current_user.id, album_audio_id))


@router.get("/lyric")
async def get_music_lyric(
    title: str = Query(..., min_length=1, description="歌曲名"),
    artist: str = Query("", description="歌手名"),
    hash: str = Query(..., min_length=1, description="音乐 hash"),
    album_audio_id: str | None = Query(None, description="专辑音频 ID"),
    duration: int = Query(0, ge=0, description="歌曲时长"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_track_lyric(current_user.id, title, artist, hash, album_audio_id, duration),
    )


# --- Comments ---

@router.get("/comment/song")
async def get_music_song_comments(
    mixsong_id: str = Query(..., alias="mixsongid", min_length=1, description="歌曲 mixsongid"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_song_comments(current_user.id, mixsong_id, page, page_size))


@router.get("/comment/song/classify")
async def get_music_song_comments_classify(
    mixsong_id: str = Query(..., alias="mixsongid", min_length=1, description="歌曲 mixsongid"),
    type_id: str = Query(..., min_length=1, description="分类 type_id"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(
        await music_service.get_song_comments_classify(current_user.id, mixsong_id, type_id, page, page_size),
    )


@router.get("/comment/song/hotword")
async def get_music_song_comments_hotword(
    mixsong_id: str = Query(..., alias="mixsongid", min_length=1, description="歌曲 mixsongid"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_song_comments_hotword(current_user.id, mixsong_id))


@router.get("/comment/floor")
async def get_music_floor_comments(
    special_id: str = Query(..., min_length=1, description="评论 special_id"),
    mixsong_id: str | None = Query(None, alias="mixsongid", description="歌曲 mixsongid"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_floor_comments(current_user.id, special_id, mixsong_id, page, page_size))


@router.get("/comment/playlist")
async def get_music_playlist_comments(
    playlist_id: str = Query(..., min_length=1, description="歌单 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_playlist_comments(current_user.id, playlist_id, page, page_size))


@router.get("/comment/album")
async def get_music_album_comments(
    album_id: str = Query(..., min_length=1, description="专辑 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_album_comments(current_user.id, album_id, page, page_size))


@router.get("/comment/count")
async def get_music_comment_counts(
    hash: str = Query(..., min_length=1, description="歌曲 hash"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_comment_counts(current_user.id, hash))


# --- Artist Follow ---

@router.post("/artist/follow")
async def follow_music_artist(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.follow_artist(current_user.id, artist_id))


@router.delete("/artist/follow")
async def unfollow_music_artist(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.unfollow_artist(current_user.id, artist_id))


@router.get("/artist/follow/newsongs")
async def get_music_followed_artist_new_songs(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_followed_artists_new_songs(current_user.id))


@router.get("/user/followed-artists")
async def get_music_user_followed_artists(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_followed_artists(current_user.id))


# --- Video / MV ---

@router.get("/video/detail")
async def get_music_video_detail(
    video_id: str = Query(..., min_length=1, description="视频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_video_detail(current_user.id, video_id))


@router.get("/video/url")
async def get_music_video_url(
    video_id: str = Query(..., min_length=1, description="视频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_video_url(current_user.id, video_id))


@router.get("/video/privilege")
async def get_music_video_privilege(
    video_id: str = Query(..., min_length=1, description="视频 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_video_privilege(current_user.id, video_id))


# --- Discovery & Recommendation Enhancements ---

@router.get("/albums/new")
async def list_music_new_albums(
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_new_albums(current_user.id, page, page_size))


@router.get("/recommend/ai")
async def get_music_ai_recommend(
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_ai_recommend_tracks(current_user.id, page_size))


@router.get("/recommend/brush")
async def get_music_brush_feed(
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_brush_feed(current_user.id, page_size))


@router.get("/recommend/everyday")
async def get_music_everyday_recommend(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_everyday_recommend(current_user.id))


@router.get("/recommend/style")
async def get_music_style_recommend(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_style_recommend(current_user.id))


@router.get("/artist/videos")
async def get_music_artist_videos(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(20, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_videos(current_user.id, artist_id, page, page_size))


@router.get("/artist/honour")
async def get_music_artist_honour(
    artist_id: str = Query(..., min_length=1, description="歌手 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_artist_honour(current_user.id, artist_id))


@router.get("/artists/directory")
async def list_music_artist_directory(
    page: int = Query(1, ge=1, le=50, description="页码"),
    page_size: int = Query(30, ge=1, le=50, description="每页数量"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.list_artist_directory(current_user.id, page, page_size))


@router.get("/rank/detail")
async def get_music_rank_detail(
    rank_id: str = Query(..., min_length=1, description="排行榜 ID"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_rank_detail(current_user.id, rank_id))


@router.get("/banner")
async def get_music_banner(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_banner_list(current_user.id))


@router.get("/search/complex")
async def search_music_complex(
    query: str = Query(..., min_length=1, max_length=100, description="搜索关键词"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    normalized_query = query.strip()
    if not normalized_query:
        return response.param_error("query cannot be empty")
    return response.success(await music_service.get_complex_search(current_user.id, normalized_query))


@router.get("/user/vip")
async def get_music_user_vip(
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.get_user_vip_detail(current_user.id))


@router.post("/auth/captcha")
async def send_music_captcha(
    phone: str = Query(..., min_length=11, max_length=11, description="phone number"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.send_captcha(phone))


@router.post("/auth/login")
async def login_music_cellphone(
    phone: str = Query(..., min_length=11, max_length=11, description="phone number"),
    captcha: str = Query(..., min_length=4, max_length=6, description="captcha code"),
    current_user: User = Depends(get_current_user),
    music_service: MusicService = Depends(get_music_service),
):
    return response.success(await music_service.login_cellphone(current_user.id, phone, captcha))
