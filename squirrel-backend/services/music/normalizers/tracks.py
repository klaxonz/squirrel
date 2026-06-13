from __future__ import annotations

from typing import Any

from services.music.normalizers.common import artist_id, artist_names, format_image_url, milliseconds_to_seconds


def normalize_track(row: dict[str, Any]) -> dict[str, Any]:
    audio_info = row.get('audio_info') if isinstance(row.get('audio_info'), dict) else {}
    album_info = row.get('album_info') if isinstance(row.get('album_info'), dict) else {}
    albuminfo = row.get('albuminfo') if isinstance(row.get('albuminfo'), dict) else {}
    base = row.get('base') if isinstance(row.get('base'), dict) else {}
    trans_param = row.get('trans_param') if isinstance(row.get('trans_param'), dict) else {}
    artist = row.get('SingerName') or row.get('author_name') or base.get('author_name') or row.get('singername') or artist_names(row)
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
        or milliseconds_to_seconds(row.get('timelen'))
        or milliseconds_to_seconds(
            audio_info.get('duration_128') or audio_info.get('duration') or row.get('timelength_128'),
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
            or '',
        ),
        'title': title,
        'artist': artist,
        'album': row.get('AlbumName') or album_info.get('album_name') or albuminfo.get('name') or row.get('album_name') or row.get('remark') or '',
        'hash': row.get('FileHash') or row.get('hash') or audio_info.get('hash_128') or audio_info.get('hash') or '',
        'album_id': str(row.get('AlbumID') or row.get('album_id') or base.get('album_id') or albuminfo.get('id') or ''),
        'album_audio_id': str(
            row.get('AlbumAudioID') or row.get('MixSongID') or row.get('album_audio_id') or row.get('add_mixsongid')
            or row.get('mixsongid') or base.get('album_audio_id') or '',
        ),
        'duration': int(duration or 0),
        'cover': format_image_url(
            row.get('Image') or row.get('image') or row.get('cover') or row.get('pic') or row.get('img')
            or row.get('imgurl') or row.get('sizable_cover') or album_info.get('sizable_cover')
            or album_info.get('cover') or album_info.get('imgurl') or albuminfo.get('sizable_cover')
            or albuminfo.get('cover') or albuminfo.get('imgurl') or trans_param.get('union_cover') or '',
        ),
    }
    current_artist_id = artist_id(row)
    if current_artist_id:
        payload['artist_id'] = current_artist_id
    file_id = str(row.get('fileid') or row.get('file_id') or '')
    if file_id:
        payload['file_id'] = file_id
    return payload
