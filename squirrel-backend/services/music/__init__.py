"""Music service public API."""

from schemas.music import MusicTrackPayload  # noqa: F401
from services.music._client import (  # noqa: F401
    KUGOU_AUTH_REDIS_KEY_PREFIX,
    MusicServiceError,
    _auth_redis_key,
    _cookie_value,
    _effective_cookie,
    _get_user_cookie,
    _request_kugou,
)
from services.music._normalizers import (  # noqa: F401
    _artist_id,
    _artist_names,
    _first_list,
    _format_image_url,
    _milliseconds_to_seconds,
    _normalize_album,
    _normalize_album_from_track,
    _normalize_artist,
    _normalize_artist_search,
    _normalize_comment,
    _normalize_hot_search,
    _normalize_mv,
    _normalize_playlist,
    _normalize_playlist_tags,
    _normalize_rank,
    _normalize_suggestion_items,
    _normalize_track,
    _normalize_user_playlist,
    _normalize_video,
    _parse_lrc,
    _parse_lrc_timestamp,
)
from services.music.album import get_album_detail, get_album_tracks  # noqa: F401
from services.music.artist import (  # noqa: F401
    follow_artist,
    get_artist_albums,
    get_artist_detail,
    get_artist_honour,
    get_artist_tracks,
    get_artist_videos,
    get_followed_artists_new_songs,
    get_user_followed_artists,
    list_artist_directory,
    unfollow_artist,
)
from services.music.comments import (  # noqa: F401
    get_album_comments,
    get_comment_counts,
    get_floor_comments,
    get_playlist_comments,
    get_song_comments,
    get_song_comments_classify,
    get_song_comments_hotword,
)
from services.music.discovery import (  # noqa: F401
    get_ai_recommend_tracks,
    get_banner_list,
    get_brush_feed,
    get_complex_search,
    get_daily_recommend_tracks,
    get_everyday_recommend,
    get_personal_fm_tracks,
    get_rank_detail,
    get_rank_tracks,
    get_recommend_card_tracks,
    get_style_recommend,
    list_new_albums,
    list_new_songs,
    list_ranks,
)
from services.music.library import (  # noqa: F401
    _playlist_track_data,
    add_track_to_user_playlist,
    collect_playlist,
    create_user_playlist,
    delete_user_playlist,
    get_favorite_counts,
    get_latest_listen_songs,
    get_playlist_tracks,
    get_related_tracks,
    get_similar_playlists,
    get_user_history,
    get_user_listen_rank,
    get_user_playlist_tracks,
    list_playlist_tags,
    list_playlists,
    list_user_playlists,
    remove_tracks_from_user_playlist,
    upload_play_history,
)
from services.music.playback import (  # noqa: F401
    get_track_climax,
    get_track_lyric,
    get_track_mv,
    get_track_play_url,
)
from services.music.search import (  # noqa: F401
    get_default_search_keyword,
    list_hot_searches,
    search_albums,
    search_artists,
    search_suggestions,
    search_tracks,
)
from services.music.user import (  # noqa: F401
    check_qr_login,
    clear_auth,
    create_qr_login,
    get_auth_status,
    get_user_profile,
    get_user_vip_detail,
    login_cellphone,
    logout,
    send_captcha,
)
from services.music.video import (  # noqa: F401
    get_video_detail,
    get_video_privilege,
    get_video_url,
)
