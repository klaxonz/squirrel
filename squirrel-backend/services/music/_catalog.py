from typing import Any

from services.music.normalizers.albums import normalize_album
from services.music.normalizers.artists import normalize_artist
from services.music.normalizers.common import first_list
from services.music.normalizers.media import normalize_video
from services.music.normalizers.tracks import normalize_track


class MusicCatalogMixin:
    # --- Album ---

    async def get_album_detail(self, user_id: int, album_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/album/detail', {'id': album_id}, user_id=user_id)
        rows = payload.get('data') if isinstance(payload.get('data'), list) else []
        row = rows[0] if rows and isinstance(rows[0], dict) else {}
        return normalize_album(row)

    async def get_album_tracks(self, user_id: int, album_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/album/songs', {
            'id': album_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        rows = data.get('songs') if isinstance(data.get('songs'), list) else []
        return {
            'items': [normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('total') or payload.get('total') or len(rows),
        }

    # --- Artist ---

    async def get_artist_detail(self, user_id: int, artist_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/detail', {'id': artist_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return normalize_artist(data)

    async def get_artist_tracks(self, user_id: int, artist_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/audios', {
            'id': artist_id,
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        rows = payload.get('data') if isinstance(payload.get('data'), list) else []
        return {
            'items': [normalize_track(row) for row in rows],
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
            'items': [normalize_album(row) for row in rows],
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
        rows = first_list(data, ('songs', 'info', 'list', 'data'))
        return {
            'items': [normalize_track(row) for row in rows],
        }

    async def get_user_followed_artists(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/follow', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('info', 'list', 'lists', 'data'))
        return {
            'items': [normalize_artist(row) for row in rows],
        }

    async def list_artist_directory(self, user_id: int, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/lists', {
            'page': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('info', 'list', 'lists', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_artist(row) for row in rows],
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
        rows = first_list(data, ('info', 'list', 'lists', 'videos', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_video(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_artist_honour(self, user_id: int, artist_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/artist/honour', {'id': artist_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('info', 'list', 'lists', 'honours', 'data'))
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

