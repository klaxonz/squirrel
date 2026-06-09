"""Music service public API — class-based with DI support."""

from typing import Any

import anyio

from core.cache import redis_client as _global_redis_client
from core.config import settings as _global_settings
from schemas.music import MusicTrackPayload
from services.music._client import MusicClient, MusicServiceError
from services.music._normalizers import (
    _first_list,
    _format_image_url,
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
)

__all__ = ['MusicService', 'MusicServiceError', 'MusicClient']


class MusicService:
    Error = MusicServiceError

    def __init__(self, redis_client=None, http_client=None, settings=None):
        self._client = MusicClient(
            redis_client=redis_client or _global_redis_client,
            http_client=http_client,
            settings=settings or _global_settings,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    # --- Search ---

    async def search_tracks(self, user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/search', {
            'keywords': query,
            'page': page,
            'pagesize': page_size,
            'type': 'song',
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('lists')
        if not isinstance(rows, list):
            rows = []

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('total') or data.get('total_count') or len(rows),
        }

    async def search_artists(self, user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/search', {
            'keywords': query,
            'page': page,
            'pagesize': page_size,
            'type': 'author',
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('lists')
        if not isinstance(rows, list):
            rows = []

        return {
            'items': [_normalize_artist_search(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('total') or len(rows),
        }

    async def search_albums(self, user_id: int, query: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/search', {
            'keywords': query,
            'page': page,
            'pagesize': min(page_size * 3, 50),
            'type': 'song',
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('lists')
        if not isinstance(rows, list):
            rows = []

        albums: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            if not isinstance(row, dict):
                continue
            album = _normalize_album_from_track(row)
            if not album['id'] or album['id'] in seen:
                continue
            seen.add(album['id'])
            albums.append(album)
            if len(albums) >= page_size:
                break

        return {
            'items': albums,
            'page': page,
            'page_size': page_size,
            'total': len(albums),
        }

    async def get_default_search_keyword(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/search/default', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        keyword = ''
        if isinstance(data, dict):
            keyword = str(data.get('keyword') or data.get('show_keyword') or data.get('word') or '')
        return {'keyword': keyword}

    async def list_hot_searches(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/search/hot', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'items', 'data'))

        return {
            'items': [_normalize_hot_search(row) for row in rows],
        }

    async def search_suggestions(self, user_id: int, query: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/search/suggest', {
            'keywords': query,
            'albumTipCount': 6,
            'correctTipCount': 6,
            'mvTipCount': 6,
            'musicTipCount': 10,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        return {
            'items': _normalize_suggestion_items(data),
        }

    async def get_complex_search(self, user_id: int, query: str) -> dict[str, Any]:
        song_payload: dict[str, Any] = {}
        artist_payload: dict[str, Any] = {}

        async def load_songs() -> None:
            nonlocal song_payload
            song_payload = await self._client.request_kugou('/search', {
                'keywords': query,
                'page': 1,
                'pagesize': 50,
                'type': 'song',
            }, user_id=user_id)

        async def load_artists() -> None:
            nonlocal artist_payload
            artist_payload = await self._client.request_kugou('/search', {
                'keywords': query,
                'page': 1,
                'pagesize': 12,
                'type': 'author',
            }, user_id=user_id)

        async with anyio.create_task_group() as task_group:
            task_group.start_soon(load_songs)
            task_group.start_soon(load_artists)

        song_data = song_payload.get('data') if isinstance(song_payload.get('data'), dict) else {}
        song_rows = song_data.get('lists')
        if not isinstance(song_rows, list):
            song_rows = []

        artist_data = artist_payload.get('data') if isinstance(artist_payload.get('data'), dict) else {}
        artist_rows = artist_data.get('lists')
        if not isinstance(artist_rows, list):
            artist_rows = []

        songs = [_normalize_track(row) for row in song_rows if isinstance(row, dict)]
        artists = [_normalize_artist_search(row) for row in artist_rows if isinstance(row, dict)]
        albums: list[dict[str, Any]] = []
        seen_album_ids: set[str] = set()
        for row in song_rows:
            if not isinstance(row, dict):
                continue
            album = _normalize_album_from_track(row)
            if not album['id'] or album['id'] in seen_album_ids:
                continue
            seen_album_ids.add(album['id'])
            albums.append(album)
            if len(albums) >= 12:
                break

        return {
            'songs': songs[:50],
            'artists': artists[:12],
            'albums': albums[:12],
        }

    # --- Album ---

    async def get_album_detail(self, user_id: int, album_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/album/detail', {'id': album_id}, user_id=user_id)
        rows = payload.get('data') if isinstance(payload.get('data'), list) else []
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        return _normalize_album(row)

    async def get_album_tracks(self, user_id: int, album_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/album/songs', {
            'id': album_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('songs') if isinstance(data.get('songs'), list) else []
        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('total') or payload.get('total') or len(rows),
        }

    # --- Artist ---

    async def get_artist_detail(self, user_id: int, artist_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/detail', {'id': artist_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return _normalize_artist(data)

    async def get_artist_tracks(self, user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/audios', {
            'id': artist_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        rows = payload.get('data') if isinstance(payload.get('data'), list) else []
        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': payload.get('total') or len(rows),
        }

    async def get_artist_albums(self, user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/albums', {
            'id': artist_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        rows = payload.get('data') if isinstance(payload.get('data'), list) else []
        return {
            'items': [_normalize_album(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': payload.get('total') or len(rows),
        }

    async def follow_artist(self, user_id: int, artist_id: str) -> dict[str, Any]:
        await self._client.request_kugou('/artist/follow', {'id': artist_id}, user_id=user_id)
        return {'ok': True}

    async def unfollow_artist(self, user_id: int, artist_id: str) -> dict[str, Any]:
        await self._client.request_kugou('/artist/unfollow', {'id': artist_id}, user_id=user_id)
        return {'ok': True}

    async def get_followed_artists_new_songs(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/follow/newsongs', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'info', 'list', 'data'))
        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def get_user_followed_artists(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/follow', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'data'))
        return {
            'items': [_normalize_artist(row) for row in rows],
        }

    async def list_artist_directory(self, user_id: int, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/lists', {
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_artist(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_artist_videos(self, user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/videos', {
            'id': artist_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'videos', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_video(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_artist_honour(self, user_id: int, artist_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/honour', {'id': artist_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'honours', 'data'))
        return {
            'items': [
                {
                    'title': str(row.get('title') or row.get('name') or ''),
                    'description': str(row.get('desc') or row.get('description') or ''),
                    'date': str(row.get('date') or row.get('time') or ''),
                }
                for row in rows
            ],
        }

    # --- Comments ---

    async def get_song_comments(self, user_id: int, mixsong_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/music', {
            'mixsongid': mixsong_id,
            'p': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or data.get('cmtcount') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_comment(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_song_comments_classify(
        self, user_id: int, mixsong_id: str, type_id: str, page: int, page_size: int,
    ) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/music/classify', {
            'mixsongid': mixsong_id,
            'type_id': type_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_comment(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_song_comments_hotword(self, user_id: int, mixsong_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/music/hotword', {
            'mixsongid': mixsong_id,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        return {
            'items': [
                {
                    'keyword': str(row.get('keyword') or row.get('word') or row.get('hotword') or ''),
                    'count': int(row.get('count') or row.get('num') or 0),
                }
                for row in rows
            ],
        }

    async def get_floor_comments(
        self, user_id: int, special_id: str, mixsong_id: str | None, page: int, page_size: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'special_id': special_id,
            'p': page,
            'pagesize': page_size,
        }
        if mixsong_id:
            params['mixsongid'] = mixsong_id
        payload = await self._client.request_kugou('/comment/floor', params, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_comment(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_playlist_comments(self, user_id: int, playlist_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/playlist', {
            'id': playlist_id,
            'p': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_comment(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_album_comments(self, user_id: int, album_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/album', {
            'id': album_id,
            'p': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_comment(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_comment_counts(self, user_id: int, hash_value: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/count', {
            'hash': hash_value,
        }, user_id=user_id, use_auth=False)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        count = 0
        if isinstance(data, dict):
            count = int(data.get('count') or data.get('cmtcount') or data.get('num') or 0)
        elif isinstance(data, (int, float)):
            count = int(data)
        return {'count': count}

    # --- Discovery ---

    async def get_personal_fm_tracks(
        self,
        user_id: int,
        mode: str = 'normal',
        song_pool_id: str | None = None,
        action: str | None = None,
        hash: str | None = None,
        songid: str | None = None,
        playtime: int | None = None,
        is_overplay: bool = False,
        remain_songcnt: int = 0,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {'mode': mode}
        if song_pool_id is not None:
            params['song_pool_id'] = song_pool_id
        if action is not None:
            params['action'] = action
        if hash is not None:
            params['hash'] = hash
        if songid is not None:
            params['songid'] = songid
        if playtime is not None:
            params['playtime'] = playtime
        if is_overplay:
            params['is_overplay'] = 1
        if remain_songcnt > 0:
            params['remain_songcnt'] = remain_songcnt

        payload = await self._client.request_kugou('/personal/fm', params, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('song_list')
        if not isinstance(rows, list):
            rows = []

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': 1,
            'page_size': len(rows),
            'total': len(rows),
        }

    async def get_recommend_card_tracks(self, user_id: int, card_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/top/card', {'card_id': card_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('song_list', 'songs', 'songlist', 'info', 'list', 'data'))
        if page_size > 0:
            rows = rows[:page_size]
        if isinstance(data, dict):
            title = str(data.get('rec_desc') or data.get('title') or '')
            total = data.get('song_list_size') or data.get('total') or len(rows)
        else:
            title = ''
            total = len(rows)

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': 1,
            'page_size': page_size,
            'total': total,
            'card_id': card_id,
            'title': title.strip('「」'),
        }

    async def get_daily_recommend_tracks(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/recommend/songs', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('song_list', 'songs', 'songlist', 'info', 'list', 'data'))
        if page_size > 0:
            rows = rows[:page_size]
        if isinstance(data, dict):
            total = data.get('song_list_size') or data.get('total') or len(rows)
            cover = _format_image_url(str(data.get('cover_img_url') or data.get('cover') or ''))
        else:
            total = len(rows)
            cover = ''

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': 1,
            'page_size': page_size,
            'total': total,
            'cover': cover,
        }

    async def list_ranks(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/rank/list', {'withsong': 0}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('info')
        if not isinstance(rows, list):
            rows = []

        return {
            'items': [_normalize_rank(row) for row in rows],
            'total': data.get('total') or len(rows),
        }

    async def get_rank_tracks(
        self, user_id: int, rank_id: str, rank_cid: str | None, page: int, page_size: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'rankid': rank_id,
            'page': page,
            'pagesize': page_size,
        }
        if rank_cid:
            params['rank_cid'] = rank_cid

        payload = await self._client.request_kugou('/rank/audio', params, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = _first_list(data, ('songlist', 'songs', 'list', 'info', 'data'))

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('total') or payload.get('total') or len(rows),
        }

    async def list_new_songs(
        self, user_id: int, category_type: int | None, page: int, page_size: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'page': page,
            'pagesize': page_size,
        }
        if category_type is not None:
            params['type'] = category_type
        payload = await self._client.request_kugou('/top/song', params, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'songlist', 'info', 'list', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def list_new_albums(self, user_id: int, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/top/album', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = []
        for key in ('chn', 'eur', 'jpn', 'kor'):
            region = data.get(key)
            if isinstance(region, list):
                rows.extend(item for item in region if isinstance(item, dict))
        start = (page - 1) * page_size
        end = start + page_size
        page_rows = rows[start:end]
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_album(row) for row in page_rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_ai_recommend_tracks(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/ai/recommend', {
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def get_brush_feed(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/brush', {
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def get_everyday_recommend(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/everyday/recommend', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def get_style_recommend(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/everyday/style/recommend', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def get_rank_detail(self, user_id: int, rank_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/rank/info', {'rankid': rank_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return {
            'id': str(data.get('rankid') or rank_id),
            'name': str(data.get('name') or data.get('rankname') or ''),
            'cover': _format_image_url(str(data.get('img') or data.get('cover') or data.get('banner') or '')),
            'intro': str(data.get('intro') or data.get('description') or ''),
            'update_frequency': str(data.get('update_frequency') or data.get('update') or ''),
            'song_count': int(data.get('song_count') or data.get('total') or 0),
        }

    async def get_banner_list(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/yueku/banner', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('banner', 'banners', 'list', 'data'))
        items = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            items.append({
                'id': str(row.get('id') or row.get('banner_id') or ''),
                'title': str(row.get('title') or row.get('name') or ''),
                'cover': _format_image_url(str(row.get('img') or row.get('image') or row.get('cover') or '')),
                'type': str(row.get('type') or row.get('action_type') or ''),
                'target_id': str(row.get('target_id') or row.get('id_extra') or ''),
            })
        return {'items': items}

    # --- Library ---

    @staticmethod
    def _playlist_track_data(track: MusicTrackPayload) -> str:
        return '|'.join([track.title, track.hash, track.album_id, track.album_audio_id])

    async def list_playlists(self, user_id: int, category_id: int, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/top/playlist', {
            'category_id': category_id,
            'page': page,
            'pagesize': page_size,
            'withsong': 0,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('special_list')
        if not isinstance(rows, list):
            rows = []

        return {
            'items': [_normalize_playlist(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'has_more': bool(data.get('has_next')),
        }

    async def list_playlist_tags(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/playlist/tags', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'tags', 'data'))
        return {
            'items': _normalize_playlist_tags(rows),
        }

    async def get_similar_playlists(self, user_id: int, playlist_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/playlist/similar', {'ids': playlist_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'special_list', 'data'))
        return {
            'items': [_normalize_playlist(row) for row in rows],
        }

    async def get_playlist_tracks(self, user_id: int, playlist_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/playlist/track/all', {
            'id': playlist_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('songs')
        if not isinstance(rows, list):
            rows = []

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('count') or len(rows),
        }

    async def list_user_playlists(self, user_id: int, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/playlist', {
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'lists', 'list', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_user_playlist(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_user_playlist_tracks(self, user_id: int, list_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/playlist/track/all/new', {
            'listid': list_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'songs', 'list', 'files', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def create_user_playlist(self, user_id: int, name: str, is_private: bool) -> dict[str, Any]:
        await self._client.request_kugou('/playlist/add', {
            'name': name,
            'type': 0,
            'is_pri': 1 if is_private else 0,
        }, user_id=user_id)
        return {'ok': True}

    async def collect_playlist(self, user_id: int, playlist_id: str) -> dict[str, Any]:
        detail_payload = await self._client.request_kugou('/playlist/detail', {'ids': playlist_id}, user_id=user_id)
        detail_rows = detail_payload.get('data') if isinstance(detail_payload.get('data'), list) else []
        detail = detail_rows[0] if detail_rows and isinstance(detail_rows[0], dict) else {}
        list_create_userid = str(detail.get('list_create_userid') or '')
        list_create_listid = str(detail.get('list_create_listid') or '')
        name = str(detail.get('name') or '')
        if not list_create_userid or not list_create_listid or not name:
            raise MusicServiceError('KuGouMusicApi playlist detail missed collect fields')

        await self._client.request_kugou('/playlist/add', {
            'name': name,
            'type': 1,
            'source': detail.get('source') or 1,
            'list_create_userid': list_create_userid,
            'list_create_listid': list_create_listid,
            'list_create_gid': detail.get('list_create_gid') or playlist_id,
        }, user_id=user_id)
        return {'ok': True}

    async def delete_user_playlist(self, user_id: int, list_id: str) -> dict[str, Any]:
        await self._client.request_kugou('/playlist/del', {'listid': list_id}, user_id=user_id)
        return {'ok': True}

    async def add_track_to_user_playlist(self, user_id: int, list_id: str, track: MusicTrackPayload) -> dict[str, Any]:
        await self._client.request_kugou('/playlist/tracks/add', {
            'listid': list_id,
            'data': self._playlist_track_data(track),
        }, user_id=user_id)
        return {'ok': True}

    async def remove_tracks_from_user_playlist(self, user_id: int, list_id: str, file_ids: str) -> dict[str, Any]:
        await self._client.request_kugou('/playlist/tracks/del', {
            'listid': list_id,
            'fileids': file_ids,
        }, user_id=user_id)
        return {'ok': True}

    async def get_user_history(self, user_id: int, bp: str | None) -> dict[str, Any]:
        params = {}
        if bp:
            params['bp'] = bp
        payload = await self._client.request_kugou('/user/history', params, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'info', 'list', 'data'))
        if isinstance(data, dict):
            next_bp = data.get('bp') or data.get('next_bp') or ''
        else:
            next_bp = ''

        return {
            'items': [_normalize_track(row) for row in rows],
            'bp': next_bp,
        }

    async def get_user_listen_rank(self, user_id: int, history_type: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/listen', {'type': history_type}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'info', 'list', 'data'))

        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def get_latest_listen_songs(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/lastest/songs/listen', {'pagesize': page_size}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('songs', 'info', 'list', 'data'))

        return {
            'items': [_normalize_track(row) for row in rows],
        }

    async def upload_play_history(
        self, user_id: int, album_audio_id: str, played_at: int | None, play_count: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'mxid': album_audio_id,
            'pc': play_count,
        }
        if played_at:
            params['time'] = played_at
        await self._client.request_kugou('/playhistory/upload', params, user_id=user_id)
        return {'ok': True}

    async def get_favorite_counts(self, user_id: int, mixsongids: str) -> dict[str, Any]:
        payload = await self._client.request_kugou(
            '/favorite/count', {'mixsongids': mixsongids}, user_id=user_id, use_auth=False,
        )
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('list') if isinstance(data.get('list'), list) else []
        return {
            'items': [
                {
                    'mixsongid': str(row.get('mixsongid') or ''),
                    'count': int(row.get('count') or 0),
                    'count_text': str(row.get('count_text') or ''),
                }
                for row in rows
                if isinstance(row, dict)
            ],
        }

    async def get_related_tracks(
        self, user_id: int, album_audio_id: str, page: int, page_size: int, sort: str, type_id: str | None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'album_audio_id': album_audio_id,
            'page': page,
            'pagesize': page_size,
            'sort': sort,
        }
        if type_id:
            params['type'] = type_id
        payload = await self._client.request_kugou(
            '/audio/related', params, user_id=user_id, use_auth=False,
        )
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'songs', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [_normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    # --- Playback ---

    async def get_track_play_url(
        self, user_id: int, hash_value: str, album_audio_id: str | None, quality: str,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'hash': hash_value,
            'quality': quality,
        }
        if album_audio_id:
            params['album_audio_id'] = album_audio_id

        payload = await self._client.request_kugou('/song/url', params, user_id=user_id)
        tracker_url = payload.get('url')
        url = ''
        if isinstance(tracker_url, str):
            url = tracker_url
        elif isinstance(tracker_url, list):
            for item in tracker_url:
                if isinstance(item, str) and item:
                    url = item
                    break

        return {
            'url': url or '',
            'quality': str(payload.get('bitRate') or payload.get('quality') or quality),
            'expires_at': payload.get('expire'),
        }

    async def get_track_lyric(
        self, user_id: int, title: str, artist: str, hash_value: str, album_audio_id: str | None, duration: int,
    ) -> dict[str, Any]:
        keyword = f'{artist} - {title}' if artist else title
        lyric_search = await self._client.request_kugou('/search/lyric', {
            'keywords': keyword,
            'hash': hash_value,
            'album_audio_id': album_audio_id or 0,
            'duration': duration,
            'man': 'no',
        }, user_id=user_id)
        candidates = lyric_search.get('candidates')
        if not isinstance(candidates, list) or not candidates:
            return {'lines': []}

        lyric_candidate = candidates[0]
        if not isinstance(lyric_candidate, dict):
            return {'lines': []}

        lyric_id = str(lyric_candidate.get('id') or '')
        access_key = str(lyric_candidate.get('accesskey') or '')
        if not lyric_id or not access_key:
            return {'lines': []}

        lyric_payload = await self._client.request_kugou('/lyric', {
            'id': lyric_id,
            'accesskey': access_key,
            'fmt': 'lrc',
            'decode': 'true',
        }, user_id=user_id)
        content = str(lyric_payload.get('decodeContent') or '')

        return {
            'lines': _parse_lrc(content),
        }

    async def get_track_mv(self, user_id: int, album_audio_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/kmr/audio/mv', {
            'album_audio_id': album_audio_id,
            'fields': 'mkv,tags,h264,h265,authors',
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = _first_list(data, ('info', 'list', 'lists', 'mvs', 'data'))
        return {
            'items': [_normalize_mv(row) for row in rows],
        }

    async def get_track_climax(self, user_id: int, hashes: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/song/climax', {'hash': hashes}, user_id=user_id, use_auth=False)
        data = payload.get('data') if isinstance(payload.get('data'), list) else []
        return {
            'items': [
                {
                    'hash': str(row.get('hash') or ''),
                    'start': int(row.get('start') or row.get('start_time') or 0),
                    'duration': int(row.get('duration') or row.get('time') or 0),
                }
                for row in data
                if isinstance(row, dict)
            ],
        }

    # --- Video ---

    async def get_video_detail(self, user_id: int, video_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/video/detail', {'id': video_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return _normalize_video(data)

    async def get_video_url(self, user_id: int, video_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/video/url', {'id': video_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        url = ''
        if isinstance(data, dict):
            url = str(data.get('url') or data.get('play_url') or data.get('video_url') or '')
        return {'url': url}

    async def get_video_privilege(self, user_id: int, video_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/video/privilege', {'id': video_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return {
            'id': str(data.get('id') or data.get('video_id') or ''),
            'playable': bool(data.get('playable') or data.get('can_play')),
            'downloadable': bool(data.get('downloadable') or data.get('can_download')),
            'quality': str(data.get('quality') or data.get('bitrate') or ''),
        }

    # --- User Auth ---

    async def get_auth_status(self, user_id: int) -> dict[str, Any]:
        user_cookie = await self._client._get_user_cookie(user_id)
        cookie = user_cookie or self._client.settings.KUGOU_MUSIC_COOKIE
        return {
            'logged_in': bool(self._client._cookie_value(cookie, 'token') and self._client._cookie_value(cookie, 'userid')),
            'source': 'redis' if user_cookie else ('env' if self._client.settings.KUGOU_MUSIC_COOKIE else ''),
            'userid': self._client._cookie_value(cookie, 'userid'),
        }

    async def clear_auth(self, user_id: int) -> None:
        await anyio.to_thread.run_sync(self._client.redis_client.delete, self._client._auth_redis_key(user_id))

    async def logout(self, user_id: int) -> dict[str, Any]:
        await self.clear_auth(user_id)
        return {'ok': True}

    async def get_user_profile(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/detail', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return {
            'userid': str(data.get('userid') or data.get('user_id') or ''),
            'nickname': data.get('nickname') or data.get('k_nickname') or data.get('user_name') or '',
            'avatar': _format_image_url(data.get('pic') or data.get('k_pic') or data.get('fx_pic') or ''),
            'level': int(data.get('p_grade') or data.get('level') or 0),
            'gender': str(data.get('gender') or ''),
            'register_time': str(data.get('rtime') or data.get('register_time') or ''),
            'follow_count': int(data.get('follows') or 0),
            'fan_count': int(data.get('fans') or 0),
            'listen_count': int(data.get('duration') or 0),
        }

    async def create_qr_login(self) -> dict[str, Any]:
        key_payload = await self._client.request_kugou('/login/qr/key', {})
        key_data = key_payload.get('data') if isinstance(key_payload.get('data'), dict) else {}
        key = key_data.get('qrcode') or key_data.get('key') or key_data.get('qr_code') or key_data.get('qrcode_txt')
        if not key:
            raise MusicServiceError('KuGouMusicApi did not return QR login key')

        qr_payload = await self._client.request_kugou('/login/qr/create', {'key': key, 'qrimg': 1})
        qr_data = qr_payload.get('data') if isinstance(qr_payload.get('data'), dict) else {}
        return {
            'key': key,
            'url': qr_data.get('url') or '',
            'base64': qr_data.get('base64') or '',
        }

    async def check_qr_login(self, user_id: int, key: str) -> dict[str, Any]:
        payload = await self._client.request_kugou(
            '/login/qr/check', {'key': key, 'timestamp': self._client._timestamp_ms()},
        )
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        status = int(data.get('status') or 0)
        if status == 4:
            await self._save_user_cookie_from_login(user_id, data)

        return {
            'status': status,
            'logged_in': status == 4,
            'auth': await self.get_auth_status(user_id),
        }

    async def _save_user_cookie_from_login(self, user_id: int, data: dict[str, Any]) -> None:
        token = str(data.get('token') or '')
        kugou_userid = str(data.get('userid') or '')
        if not token or not kugou_userid:
            raise MusicServiceError('KuGouMusicApi login response missed token or userid')

        dfid = self._client._cookie_value(await self._client._effective_cookie(user_id), 'dfid')
        if not dfid:
            register_payload = await self._client.request_kugou('/register/dev', {}, use_auth=False)
            register_data = register_payload.get('data') if isinstance(register_payload.get('data'), dict) else {}
            dfid = str(register_data.get('dfid') or '')

        if not dfid:
            raise MusicServiceError('KuGouMusicApi did not return dfid')

        await anyio.to_thread.run_sync(
            self._client.redis_client.set,
            self._client._auth_redis_key(user_id),
            f'token={token};userid={kugou_userid};dfid={dfid}',
        )

    async def get_user_vip_detail(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/vip/detail', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return {
            'is_vip': bool(data.get('is_vip') or data.get('vip_type')),
            'vip_type': int(data.get('vip_type') or 0),
            'vip_expire_time': str(data.get('vip_expire_time') or data.get('expire_time') or ''),
            'vip_level': int(data.get('vip_level') or 0),
        }

    async def send_captcha(self, phone: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/captcha/sent', {'phone': phone}, use_auth=False)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return {
            'ok': bool(data.get('ok') or payload.get('ok')),
        }

    async def login_cellphone(self, user_id: int, phone: str, captcha: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/login/cellphone', {
            'phone': phone,
            'captcha': captcha,
        }, use_auth=False)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}

        if payload.get('ok') or data.get('token'):
            await self._save_user_cookie_from_login(user_id, data)
            return {
                'ok': True,
                'logged_in': True,
                'auth': await self.get_auth_status(user_id),
            }

        raise MusicServiceError(payload.get('message') or payload.get('msg') or 'Login failed')
