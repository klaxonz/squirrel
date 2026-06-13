from typing import Any

from services.music.normalizers.common import first_list
from services.music.normalizers.lyrics import parse_lrc
from services.music.normalizers.media import normalize_mv


class MusicPlaybackMixin:
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
            'lines': parse_lrc(content),
        }

    async def get_track_mv(self, user_id: int, album_audio_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/kmr/audio/mv', {
            'album_audio_id': album_audio_id,
            'fields': 'mkv,tags,h264,h265,authors',
        }, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else payload
        rows = first_list(data, ('info', 'list', 'lists', 'mvs', 'data'))
        return {
            'items': [normalize_mv(row) for row in rows],
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

