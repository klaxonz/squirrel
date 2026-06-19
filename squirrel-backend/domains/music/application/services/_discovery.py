from typing import Any

from domains.music.application.services.normalizers.albums import normalize_album
from domains.music.application.services.normalizers.common import first_list, format_image_url
from domains.music.application.services.normalizers.discovery import normalize_rank
from domains.music.application.services.normalizers.tracks import normalize_track


class MusicDiscoveryMixin:
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
            'items': [normalize_track(row) for row in rows],
            'page': 1,
            'page_size': len(rows),
            'total': len(rows),
        }

    async def get_recommend_card_tracks(self, user_id: int, card_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/top/card', {'card_id': card_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('song_list', 'songs', 'songlist', 'info', 'list', 'data'))
        if page_size > 0:
            rows = rows[:page_size]
        if isinstance(data, dict):
            title = str(data.get('rec_desc') or data.get('title') or '')
            total = data.get('song_list_size') or data.get('total') or len(rows)
        else:
            title = ''
            total = len(rows)

        return {
            'items': [normalize_track(row) for row in rows],
            'page': 1,
            'page_size': page_size,
            'total': total,
            'card_id': card_id,
            'title': title.strip('「」'),
        }

    async def get_daily_recommend_tracks(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/recommend/songs', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('song_list', 'songs', 'songlist', 'info', 'list', 'data'))
        if page_size > 0:
            rows = rows[:page_size]
        if isinstance(data, dict):
            total = data.get('song_list_size') or data.get('total') or len(rows)
            cover = format_image_url(str(data.get('cover_img_url') or data.get('cover') or ''))
        else:
            total = len(rows)
            cover = ''

        return {
            'items': [normalize_track(row) for row in rows],
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
            'items': [normalize_rank(row) for row in rows],
            'total': data.get('total') or len(rows),
        }

    async def get_rank_tracks(
        self,
        user_id: int,
        rank_id: str,
        rank_cid: str | None,
        page: int,
        page_size: int,
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
        rows = first_list(data, ('songlist', 'songs', 'list', 'info', 'data'))

        return {
            'items': [normalize_track(row) for row in rows],
            'page': page,
            'page_size': page_size,
            'total': data.get('total') or payload.get('total') or len(rows),
        }

    async def list_new_songs(
        self,
        user_id: int,
        category_type: int | None,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {
            'page': page,
            'pagesize': page_size,
        }
        if category_type is not None:
            params['type'] = category_type
        payload = await self._client.request_kugou('/top/song', params, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'songlist', 'info', 'list', 'data'))
        total = data.get('total') or data.get('count') or len(rows) if isinstance(data, dict) else len(rows)

        return {
            'items': [normalize_track(row) for row in rows],
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
        total = data.get('total') or data.get('count') or len(rows) if isinstance(data, dict) else len(rows)

        return {
            'items': [normalize_album(row) for row in page_rows],
            'page': page,
            'page_size': page_size,
            'total': total,
        }

    async def get_ai_recommend_tracks(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou(
            '/ai/recommend',
            {
                'pagesize': page_size,
            },
            user_id=user_id,
        )
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [normalize_track(row) for row in rows],
        }

    async def get_brush_feed(self, user_id: int, page_size: int) -> dict[str, Any]:
        payload = await self._client.request_kugou(
            '/brush',
            {
                'pagesize': page_size,
            },
            user_id=user_id,
        )
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [normalize_track(row) for row in rows],
        }

    async def get_everyday_recommend(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/everyday/recommend', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [normalize_track(row) for row in rows],
        }

    async def get_style_recommend(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/everyday/style/recommend', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('songs', 'song_list', 'info', 'list', 'data'))
        return {
            'items': [normalize_track(row) for row in rows],
        }

    async def get_rank_detail(self, user_id: int, rank_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/rank/info', {'rankid': rank_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return {
            'id': str(data.get('rankid') or rank_id),
            'name': str(data.get('name') or data.get('rankname') or ''),
            'cover': format_image_url(str(data.get('img') or data.get('cover') or data.get('banner') or '')),
            'intro': str(data.get('intro') or data.get('description') or ''),
            'update_frequency': str(data.get('update_frequency') or data.get('update') or ''),
            'song_count': int(data.get('song_count') or data.get('total') or 0),
        }

    async def get_banner_list(self, user_id: int) -> dict[str, Any]:
        payload = await self._client.request_kugou('/yueku/banner', {}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('banner', 'banners', 'list', 'data'))
        items = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            items.append(
                {
                    'id': str(row.get('id') or row.get('banner_id') or ''),
                    'title': str(row.get('title') or row.get('name') or ''),
                    'cover': format_image_url(str(row.get('img') or row.get('image') or row.get('cover') or '')),
                    'type': str(row.get('type') or row.get('action_type') or ''),
                    'target_id': str(row.get('target_id') or row.get('id_extra') or ''),
                }
            )
        return {'items': items}
