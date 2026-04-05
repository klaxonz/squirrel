from __future__ import annotations

from .youtubei_resolver import YoutubeiFormat, YoutubeiResult


def _mime_parts(mime_type: str | None) -> tuple[str | None, str | None]:
    if not mime_type:
        return None, None
    base, _, rest = mime_type.partition(';')
    codecs = None
    for part in rest.split(';'):
        if 'codecs=' in part:
            codecs = part.split('=', 1)[1].strip().strip('"')
            break
    return base.strip() or None, codecs


def _codec_family(mime_type: str | None) -> str | None:
    _, codecs = _mime_parts(mime_type)
    value = (codecs or '').lower()
    if not value or value == 'none':
        return None
    primary = value.split(',', 1)[0].strip()
    if primary.startswith('av01'):
        return 'av1'
    if primary.startswith(('avc1', 'avc3', 'h264')):
        return 'avc'
    if primary.startswith(('vp09', 'vp9')):
        return 'vp9'
    if primary.startswith('mp4a'):
        return 'aac'
    if primary.startswith('opus'):
        return 'opus'
    return primary.split('.', 1)[0]


def _sort_formats(formats: list[YoutubeiFormat]) -> list[YoutubeiFormat]:
    return sorted(
        formats,
        key=lambda item: (item.height or 0, item.bitrate or 0),
        reverse=True,
    )


def map_youtubei_result(video_id: int | str, result: YoutubeiResult) -> dict:
    progressive = _sort_formats([
        fmt for fmt in result.formats
        if fmt.has_audio and fmt.has_video and fmt.url
    ])
    video_only = _sort_formats([
        fmt for fmt in result.formats
        if fmt.has_video and not fmt.has_audio and fmt.url
    ])
    audio_only = _sort_formats([
        fmt for fmt in result.formats
        if fmt.has_audio and not fmt.has_video and fmt.url
    ])
    quality_candidates = _sort_formats([
        fmt for fmt in result.formats
        if fmt.has_video and not fmt.has_audio
    ])
    if not quality_candidates:
        quality_candidates = _sort_formats([
            fmt for fmt in result.formats
            if fmt.has_audio and fmt.has_video
        ])

    if not progressive and not video_only:
        raise ValueError('youtubei primary result is incomplete')

    qualities = []
    for index, fmt in enumerate(quality_candidates):
        label = fmt.quality_label or (f'{fmt.height}p' if fmt.height else str(fmt.itag))
        qualities.append({
            'value': str(fmt.itag) if fmt.itag is not None else label,
            'label': label,
            'height': fmt.height,
            'bandwidth': fmt.bitrate,
            'codec': _codec_family(fmt.mime_type),
            'id': str(fmt.itag) if fmt.itag is not None else None,
            'index': index,
        })

    best_progressive = progressive[0] if progressive else None
    best_video_only = video_only[0] if video_only else None
    best_audio_only = audio_only[0] if audio_only else None
    has_adaptive_set = bool(video_only and audio_only)

    return {
        'video_url': (best_progressive.url if best_progressive else None) or (best_video_only.url if best_video_only else None),
        'audio_url': best_audio_only.url if best_audio_only else None,
        'mpd_url': f'/api/video/mpd?video_id={video_id}' if has_adaptive_set else None,
        'qualities': qualities or None,
    }
