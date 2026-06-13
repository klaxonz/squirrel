from typing import Any

from domains.music.application.services.normalizers.media import normalize_video


class MusicVideoMixin:
    # --- Video ---

    async def get_video_detail(self, user_id: int, video_id: str) -> dict[str, Any]:
        payload = await self._client.request_kugou('/video/detail', {'id': video_id}, user_id=user_id)
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}
        return normalize_video(data)

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

