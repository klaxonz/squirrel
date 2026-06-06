"""KuGou payload normalizers and small parsing helpers.

All functions here are pure (or close to pure): they take a raw Kugou dict
and return a normalized response shape. Shared by every domain module.
"""

from typing import Any


def _format_image_url(value: str) -> str:
    return value.replace('{size}', '240') if value else ''


def _parse_lrc(content: str) -> list[dict[str, Any]]:
    lines = []
    for raw_line in content.splitlines():
        if not raw_line.startswith('[') or ']' not in raw_line:
            continue
        text = raw_line[raw_line.rfind(']') + 1:].strip()
        for timestamp in raw_line[:raw_line.rfind(']') + 1].split(']'):
            if not timestamp.startswith('['):
                continue
            seconds = _parse_lrc_timestamp(timestamp[1:])
            if seconds >= 0:
                lines.append({'time': seconds, 'text': text})
    return sorted(lines, key=lambda item: item['time'])


def _parse_lrc_timestamp(value: str) -> float:
    if ':' not in value:
        return -1
    minutes_text, seconds_text = value.split(':', 1)
    try:
        return int(minutes_text) * 60 + float(seconds_text)
    except ValueError:
        return -1


def _milliseconds_to_seconds(value: Any) -> int:
    try:
        milliseconds = int(value or 0)
    except (TypeError, ValueError):
        return 0
    if milliseconds > 1000:
        return round(milliseconds / 1000)
    return milliseconds


def _artist_names(row: dict[str, Any]) -> str:
    for key in ('authors', 'singerinfo'):
        rows = row.get(key)
        if isinstance(rows, list):
            names = []
            for item in rows:
                if isinstance(item, dict):
                    name = item.get('author_name') or item.get('name')
                    if name:
                        names.append(name)
            if names:
                return '、'.join(names)
    return ''


def _artist_id(row: dict[str, Any]) -> str:
    for key in ('SingerId', 'author_id', 'singerid'):
        if row.get(key):
            return str(row.get(key))
    for key in ('authors', 'singerinfo'):
        rows = row.get(key)
        if isinstance(rows, list):
            for item in rows:
                if isinstance(item, dict) and (item.get('author_id') or item.get('id')):
                    return str(item.get('author_id') or item.get('id'))
    return ''


def _first_list(data: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if not isinstance(data, dict):
        return []
    for key in keys:
        value = data.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def _normalize_track(row: dict[str, Any]) -> dict[str, Any]:
    audio_info = row.get('audio_info') if isinstance(row.get('audio_info'), dict) else {}
    album_info = row.get('album_info') if isinstance(row.get('album_info'), dict) else {}
    albuminfo = row.get('albuminfo') if isinstance(row.get('albuminfo'), dict) else {}
    base = row.get('base') if isinstance(row.get('base'), dict) else {}
    trans_param = row.get('trans_param') if isinstance(row.get('trans_param'), dict) else {}
    artist = row.get('SingerName') or row.get('author_name') or base.get('author_name') or row.get('singername') or _artist_names(row)
    title = (
        row.get('SongName') or row.get('FileName') or row.get('songname') or base.get('audio_name')
        or row.get('audio_name') or row.get('name') or ''
    )
    if title and artist:
        title = str(title).strip()
        for suffix in ('.mp3', '.flac', '.m4a', '.aac', '.wav', '.ogg'):
            if title.lower().endswith(suffix):
                title = title[:-len(suffix)].strip()
                break
        for artist_name in [str(artist), *str(artist).split('、')]:
            prefix = f'{artist_name} - '
            if title.startswith(prefix):
                title = title[len(prefix):].strip()
                break
    duration = (
        row.get('Duration')
        or row.get('time_length')
        or _milliseconds_to_seconds(row.get('timelen'))
        or _milliseconds_to_seconds(
            audio_info.get('duration_128') or audio_info.get('duration') or row.get('timelength_128')
        )
    )
    payload = {
        'id': str(
            row.get('AlbumAudioID')
            or row.get('MixSongID')
            or row.get('album_audio_id')
            or row.get('add_mixsongid')
            or row.get('mixsongid')
            or base.get('album_audio_id')
            or row.get('Audioid')
            or row.get('audio_id')
            or row.get('FileHash')
            or row.get('hash')
            or ''
        ),
        'title': title,
        'artist': artist,
        'album': row.get('AlbumName') or album_info.get('album_name') or albuminfo.get('name') or row.get('album_name') or row.get('remark') or '',
        'hash': row.get('FileHash') or row.get('hash') or audio_info.get('hash_128') or audio_info.get('hash') or '',
        'album_id': str(row.get('AlbumID') or row.get('album_id') or base.get('album_id') or albuminfo.get('id') or ''),
        'album_audio_id': str(
            row.get('AlbumAudioID') or row.get('MixSongID') or row.get('album_audio_id') or row.get('add_mixsongid')
            or row.get('mixsongid') or base.get('album_audio_id') or ''
        ),
        'duration': int(duration or 0),
        'cover': _format_image_url(
            row.get('Image') or row.get('image') or row.get('cover') or row.get('pic') or row.get('img')
            or row.get('imgurl') or row.get('sizable_cover') or album_info.get('sizable_cover')
            or album_info.get('cover') or album_info.get('imgurl') or albuminfo.get('sizable_cover')
            or albuminfo.get('cover') or albuminfo.get('imgurl') or trans_param.get('union_cover') or ''
        ),
    }
    artist_id = _artist_id(row)
    if artist_id:
        payload['artist_id'] = artist_id
    file_id = str(row.get('fileid') or row.get('file_id') or '')
    if file_id:
        payload['file_id'] = file_id
    return payload


def _normalize_artist(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('author_id') or ''),
        'name': row.get('author_name') or '',
        'avatar': _format_image_url(row.get('sizable_avatar') or ''),
        'intro': row.get('intro') or '',
        'song_count': int(row.get('song_count') or 0),
        'album_count': int(row.get('album_count') or 0),
        'fan_count': int(row.get('fansnums') or 0),
    }


def _normalize_artist_search(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('AuthorId') or row.get('author_id') or ''),
        'name': row.get('AuthorName') or row.get('author_name') or '',
        'avatar': _format_image_url(row.get('Avatar') or row.get('sizable_avatar') or ''),
        'intro': row.get('Auxiliary') or row.get('intro') or '',
        'song_count': int(row.get('AudioCount') or row.get('song_count') or 0),
        'album_count': int(row.get('AlbumCount') or row.get('album_count') or 0),
        'fan_count': int(row.get('FansNum') or row.get('fansnums') or 0),
    }


def _normalize_album(row: dict[str, Any]) -> dict[str, Any]:
    authors = row.get('authors') if isinstance(row.get('authors'), list) else []
    first_author = next((item for item in authors if isinstance(item, dict)), {})
    album_id = str(row.get('album_id') or row.get('albumid') or '')
    album_name = row.get('album_name') or row.get('albumname') or ''
    cover = row.get('sizable_cover') or row.get('imgurl') or ''
    artist = row.get('author_name') or row.get('singername') or first_author.get('author_name') or ''
    artist_id = str(row.get('singerid') or first_author.get('author_id') or '')
    publish_date = row.get('publish_date') or row.get('publishtime') or ''
    
    return {
        'id': album_id,
        'name': album_name,
        'cover': _format_image_url(cover),
        'intro': row.get('intro') or '',
        'artist': artist,
        'artist_id': artist_id,
        'publish_date': publish_date.split()[0] if publish_date else '',
        'language': row.get('language') or '',
        'type': row.get('type') or '',
        'heat': int(row.get('heat') or 0),
    }


def _normalize_album_from_track(row: dict[str, Any]) -> dict[str, Any]:
    album_info = row.get('album_info') if isinstance(row.get('album_info'), dict) else {}
    album_id = str(row.get('AlbumID') or row.get('album_id') or '')
    album_name = row.get('AlbumName') or album_info.get('album_name') or row.get('album_name') or ''
    artist_id = _artist_id(row)
    return {
        'id': album_id,
        'name': album_name,
        'cover': _format_image_url(row.get('Image') or row.get('cover') or album_info.get('sizable_cover') or ''),
        'intro': '',
        'artist': row.get('SingerName') or row.get('author_name') or _artist_names(row),
        'artist_id': artist_id,
        'publish_date': '',
        'language': '',
        'type': '',
        'heat': 0,
    }


def _normalize_playlist(row: dict[str, Any]) -> dict[str, Any]:
    tags = row.get('tags')
    if not isinstance(tags, list):
        tags = []

    return {
        'id': str(row.get('global_collection_id') or ''),
        'name': row.get('specialname') or '',
        'cover': _format_image_url(row.get('flexible_cover') or row.get('imgurl') or ''),
        'intro': row.get('intro') or '',
        'creator': row.get('nickname') or '',
        'play_count': int(row.get('play_count') or 0),
        'collect_count': int(row.get('collectcount') or 0),
        'tags': [tag.get('tag_name') for tag in tags if isinstance(tag, dict) and tag.get('tag_name')],
        'list_create_userid': str(row.get('list_create_userid') or row.get('suid') or ''),
        'list_create_listid': str(row.get('list_create_listid') or row.get('specialid') or ''),
        'list_create_gid': str(row.get('list_create_gid') or row.get('global_collection_id') or ''),
    }


def _normalize_playlist_tags(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tags = []
    for group in rows:
        children = group.get('children') if isinstance(group.get('children'), list) else group.get('tags')
        if not isinstance(children, list):
            children = [group]
        for row in children:
            if not isinstance(row, dict):
                continue
            tag_id = str(row.get('tag_id') or row.get('id') or row.get('category_id') or '')
            name = str(row.get('tag_name') or row.get('name') or row.get('category_name') or '')
            if tag_id and name:
                tags.append({
                    'id': tag_id,
                    'name': name,
                    'parent_name': str(group.get('tag_name') or group.get('name') or ''),
                })
    return tags


def _normalize_user_playlist(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('listid') or row.get('list_id') or row.get('id') or ''),
        'name': row.get('name') or row.get('listname') or row.get('specialname') or '',
        'cover': _format_image_url(row.get('pic') or row.get('cover') or row.get('imgurl') or ''),
        'song_count': int(row.get('count') or row.get('song_count') or row.get('filecount') or 0),
        'is_default': bool(row.get('is_default') or row.get('is_def')),
        'is_collected': bool(row.get('is_collected') or row.get('type') == 1),
        'list_create_userid': str(row.get('list_create_userid') or row.get('userid') or ''),
        'list_create_listid': str(row.get('list_create_listid') or row.get('listid') or ''),
        'list_create_gid': str(row.get('list_create_gid') or row.get('gid') or ''),
    }


def _normalize_rank(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('rankid') or row.get('id') or ''),
        'rank_cid': str(row.get('rank_cid') or ''),
        'name': row.get('rankname') or '',
        'cover': _format_image_url(row.get('imgurl') or row.get('album_img_9') or row.get('banner_9') or ''),
        'intro': row.get('intro') or '',
        'update_frequency': row.get('update_frequency') or '',
        'play_count': int(row.get('play_times') or 0),
    }


def _normalize_hot_search(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'keyword': str(row.get('keyword') or row.get('word') or row.get('name') or row.get('search_word') or ''),
        'score': int(row.get('score') or row.get('hot') or row.get('heat') or 0),
        'jump_url': str(row.get('jump_url') or row.get('url') or ''),
    }


def _normalize_suggestion_items(data: Any) -> list[dict[str, Any]]:
    rows = _first_list(data, ('info', 'list', 'lists', 'data'))
    if not rows and isinstance(data, dict):
        for value in data.values():
            if isinstance(value, list):
                rows.extend(item for item in value if isinstance(item, dict))
    return [
        {
            'keyword': str(row.get('keyword') or row.get('HintInfo') or row.get('name') or row.get('SongName') or ''),
            'type': str(row.get('type') or row.get('search_type') or row.get('RecordType') or ''),
        }
        for row in rows
    ]


def _normalize_mv(row: dict[str, Any]) -> dict[str, Any]:
    return {
        'id': str(row.get('id') or row.get('video_id') or row.get('mv_id') or ''),
        'name': str(row.get('name') or row.get('title') or row.get('filename') or ''),
        'hash': str(row.get('hash') or row.get('mv_hash') or row.get('FileHash') or ''),
        'cover': _format_image_url(row.get('cover') or row.get('img') or row.get('imgurl') or ''),
        'duration': int(row.get('duration') or row.get('time_length') or 0),
    }


def _normalize_comment(row: dict[str, Any]) -> dict[str, Any]:
    user_info = row.get('user_info') if isinstance(row.get('user_info'), dict) else {}
    user = row.get('user') if isinstance(row.get('user'), dict) else {}
    merged_user = {**user, **user_info} if user else user_info
    content = str(row.get('content') or row.get('msg') or row.get('message') or row.get('cmtcontent') or '')
    return {
        'id': str(row.get('id') or row.get('comment_id') or row.get('specialid') or row.get('cmtid') or ''),
        'content': content,
        'user_name': str(
            merged_user.get('nickname') or merged_user.get('user_name') or merged_user.get('user_nickname')
            or row.get('user_name') or row.get('nickname') or row.get('nick_name') or ''
        ),
        'user_avatar': _format_image_url(
            merged_user.get('pic') or merged_user.get('avatar') or merged_user.get('user_pic')
            or row.get('user_pic') or row.get('avatar') or row.get('user_avatar') or ''
        ),
        'user_id': str(merged_user.get('userid') or merged_user.get('user_id') or row.get('userid') or ''),
        'like_count': int(row.get('likecount') or row.get('like_count') or row.get('support') or row.get('support_count') or 0),
        'reply_count': int(row.get('replycount') or row.get('reply_count') or row.get('reply_num') or 0),
        'created_at': str(row.get('addtime') or row.get('add_time') or row.get('create_time') or row.get('creattime') or ''),
    }


def _normalize_video(row: dict[str, Any]) -> dict[str, Any]:
    authors = row.get('authors') if isinstance(row.get('authors'), list) else []
    author_name = ''
    for author in authors:
        if isinstance(author, dict):
            name = author.get('author_name') or author.get('name')
            if name:
                author_name = name
                break
    return {
        'id': str(row.get('id') or row.get('video_id') or row.get('mv_id') or ''),
        'name': str(row.get('name') or row.get('title') or row.get('filename') or ''),
        'cover': _format_image_url(row.get('cover') or row.get('img') or row.get('imgurl') or row.get('cover_url') or ''),
        'duration': int(row.get('duration') or row.get('time_length') or 0),
        'play_count': int(row.get('play_count') or row.get('playcount') or 0),
        'artist': author_name or str(row.get('author_name') or row.get('singer_name') or ''),
        'artist_id': str(row.get('author_id') or row.get('singer_id') or ''),
    }
