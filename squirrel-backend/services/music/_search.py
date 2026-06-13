from typing import Any

import anyio

from services.music.normalizers.albums import normalize_album_from_track
from services.music.normalizers.artists import normalize_artist_search
from services.music.normalizers.common import first_list
from services.music.normalizers.search import normalize_hot_search, normalize_suggestion_items
from services.music.normalizers.tracks import normalize_track


class MusicSearchMixin:
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
            'items': [normalize_track(row) for row in rows],
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
            'items': [normalize_artist_search(row) for row in rows],
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
            album = normalize_album_from_track(row)
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
        rows = first_list(data, ('info', 'list', 'lists', 'items', 'data'))

        return {
            'items': [normalize_hot_search(row) for row in rows],
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
            'items': normalize_suggestion_items(data),
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

        songs = [normalize_track(row) for row in song_rows if isinstance(row, dict)]
        artists = [normalize_artist_search(row) for row in artist_rows if isinstance(row, dict)]
        albums: list[dict[str, Any]] = []
        seen_album_ids: set[str] = set()
        for row in song_rows:
            if not isinstance(row, dict):
                continue
            album = normalize_album_from_track(row)
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

