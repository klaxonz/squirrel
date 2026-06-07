from __future__ import annotations

import logging

from crawl import LoginStatusResult, check_login_status

logger = logging.getLogger(__name__)

_CHECK_URL = 'https://api.bilibili.com/x/web-interface/nav'
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
    'Referer': 'https://www.bilibili.com',
}


def check_bilibili_login_status() -> LoginStatusResult:
    return check_login_status(
        site_name='bilibili',
        default_check_url=_CHECK_URL,
        base_headers=_HEADERS,
        default_timeout=15,
        parse_response=_parse_response,
    )


def _parse_response(resp) -> LoginStatusResult:
    site_name = 'bilibili'
    payload = resp.json()
    if payload.get('code') == 0:
        data = payload.get('data') or {}
        if data.get('isLogin'):
            level_info = data.get('level_info') or {}
            extra = {
                'level': level_info.get('current_level'),
                'vipType': data.get('vipType'),
            }
            return LoginStatusResult(
                site_name=site_name,
                logged_in=True,
                username=data.get('uname'),
                user_id=str(data.get('mid') or ''),
                message='已登录',
                extra=extra,
            )

    message = payload.get('message') or payload.get('data', {}).get('message')
    return LoginStatusResult(
        site_name=site_name,
        logged_in=False,
        message=message or '未登录或 Cookie 已过期',
    )
