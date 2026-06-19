from typing import Any

import anyio

from domains.music.application.services._client import MusicServiceError
from domains.music.application.services.normalizers.common import format_image_url


class MusicAuthMixin:
    # --- User Auth ---

    async def get_auth_status(self, user_id: int) -> dict[str, Any]:
        user_cookie = await self._client._get_user_cookie(user_id)
        cookie = user_cookie or self._client.settings.kugou_music.cookie
        return {
            'logged_in': bool(
                self._client._cookie_value(cookie, 'token') and self._client._cookie_value(cookie, 'userid')
            ),
            'source': 'redis' if user_cookie else ('env' if self._client.settings.kugou_music.cookie else ''),
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
            'avatar': format_image_url(data.get('pic') or data.get('k_pic') or data.get('fx_pic') or ''),
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
            '/login/qr/check',
            {'key': key, 'timestamp': self._client._timestamp_ms()},
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
        payload = await self._client.request_kugou(
            '/login/cellphone',
            {
                'phone': phone,
                'captcha': captcha,
            },
            use_auth=False,
        )
        data = payload.get('data') if isinstance(payload.get('data'), dict) else {}

        if payload.get('ok') or data.get('token'):
            await self._save_user_cookie_from_login(user_id, data)
            return {
                'ok': True,
                'logged_in': True,
                'auth': await self.get_auth_status(user_id),
            }

        raise MusicServiceError(payload.get('message') or payload.get('msg') or 'Login failed')
