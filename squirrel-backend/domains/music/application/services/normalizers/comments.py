from __future__ import annotations

from typing import Any

from domains.music.application.services.normalizers.common import format_image_url


def normalize_comment(row: dict[str, Any]) -> dict[str, Any]:
    user_info = row.get('user_info') if isinstance(row.get('user_info'), dict) else {}
    user = row.get('user') if isinstance(row.get('user'), dict) else {}
    merged_user = {**user, **user_info} if user else user_info
    content = str(row.get('content') or row.get('msg') or row.get('message') or row.get('cmtcontent') or '')
    return {
        'id': str(row.get('id') or row.get('comment_id') or row.get('specialid') or row.get('cmtid') or ''),
        'content': content,
        'user_name': str(
            merged_user.get('nickname') or merged_user.get('user_name') or merged_user.get('user_nickname')
            or row.get('user_name') or row.get('nickname') or row.get('nick_name') or '',
        ),
        'user_avatar': format_image_url(
            merged_user.get('pic') or merged_user.get('avatar') or merged_user.get('user_pic')
            or row.get('user_pic') or row.get('avatar') or row.get('user_avatar') or '',
        ),
        'user_id': str(merged_user.get('userid') or merged_user.get('user_id') or row.get('userid') or ''),
        'like_count': int(row.get('likecount') or row.get('like_count') or row.get('support') or row.get('support_count') or 0),
        'reply_count': int(row.get('replycount') or row.get('reply_count') or row.get('reply_num') or 0),
        'created_at': str(row.get('addtime') or row.get('add_time') or row.get('create_time') or row.get('creattime') or ''),
    }
