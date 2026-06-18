from typing import Any

from domains.music.application.services._client import MusicServiceError
from domains.music.application.services.normalizers.common import first_list
from domains.music.application.services.normalizers.playlists import (
    normalize_playlist,
    normalize_playlist_tags,
    normalize_user_playlist,
)
from domains.music.application.services.normalizers.tracks import normalize_track
from domains.music.interfaces.dto.music import MusicTrackPayload


class MusicLibraryMixin:
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
            'items': [normalize_playlist(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'has_more': bool(data.get('has_next')),
        }

    async def list_playlist_tags(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/playlist/tags', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('info', 'list', 'tags', 'data'))
        return {
            'items': normalize_playlist_tags(rows),
        }

    async def get_similar_playlists(self, user_id: int, playlist_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/playlist/similar', {'ids': playlist_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('info', 'list', 'lists', 'special_list', 'data'))
        return {
            'items': [normalize_playlist(row) for row in rows],
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
            'items': [normalize_track(row) for row in rows],
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
        rows = first_list(data, ('info', 'lists', 'list', 'data'))
        total = (
            data.get('total') or data.get('count') or len(rows)
            if isinstance(data, dict)
            else len(rows)
        )

        return {
            'items': [normalize_user_playlist(row) for row in rows],
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
        rows = first_list(data, ('info', 'songs', 'list', 'files', 'data'))
        total = (
            data.get('total') or data.get('count') or len(rows)
            if isinstance(data, dict)
            else len(rows)
        )

        return {
            'items': [normalize_track(row) for row in rows],
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
        rows = first_list(data, ('songs', 'info', 'list', 'data'))
        next_bp = (
            data.get('bp') or data.get('next_bp') or ''
            if isinstance(data, dict)
            else ''
        )

        return {
            'items': [normalize_track(row) for row in rows],
            'bp': next_bp,
        }

    async def get_user_listen_rank(self, user_id: int, history_type: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/user/listen', {'type': history_type}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'info', 'list', 'data'))

        return {
            'items': [normalize_track(row) for row in rows],
        }

    async def get_latest_listen_songs(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/lastest/songs/listen', {'pagesize': page_size}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'info', 'list', 'data'))

        return {
            'items': [normalize_track(row) for row in rows],
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
        rows = first_list(data, ('info', 'list', 'lists', 'songs', 'data'))
        total = (
            data.get('total') or data.get('count') or len(rows)
            if isinstance(data, dict)
            else len(rows)
        )

        return {
            'items': [normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }
