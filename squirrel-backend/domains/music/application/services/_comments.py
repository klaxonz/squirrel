from typing import Any

from domains.music.application.services.normalizers.comments import normalize_comment
from domains.music.application.services.normalizers.common import first_list


class MusicCommentsMixin:
    # --- Comments ---

    async def get_song_comments(self, user_id: int, mixsong_id: str, page: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/music', {
            'mixsongid': mixsong_id,
            'p': page,
            'pagesize': page_size,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or data.get('cmtcount') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_comment(row) for row in rows],
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
        rows = first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_comment(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_song_comments_hotword(self, user_id: int, mixsong_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/comment/music/hotword', {
            'mixsongid': mixsong_id,
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
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
        rows = first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_comment(row) for row in rows],
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
        rows = first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_comment(row) for row in rows],
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
        rows = first_list(data, ('cmtlist', 'list', 'lists', 'comments', 'info', 'items', 'data'))
        if isinstance(data, dict):
            total = data.get('total') or data.get('count') or len(rows)
        else:
            total = len(rows)

        return {
            'items': [normalize_comment(row) for row in rows],
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

